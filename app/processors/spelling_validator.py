"""Custom frame processor: validates spelling attempts across multiple rounds.

Design:
  * CODE owns correctness judgment — the LLM never decides.
  * On each user TranscriptionFrame (final STT result):
      1. If the verdict phase is active (_awaiting_verdict), consume silently.
      2. Otherwise run _extract_spelling — if no valid run found, pass to LLM.
      3. If a valid spelling is extracted: judge, advance game, push
         RTVIServerMessageFrame, inject LLMMessagesAppendFrame verdict,
         and enter verdict phase.
  * _awaiting_verdict is True from the moment of judgment until BotStoppedSpeakingFrame
    arrives, preventing Deepgram's segmented transcriptions (multiple final frames for
    one slow spelling) from being double-judged or causing the LLM to fire twice.
  * BotStartedSpeakingFrame and BotStoppedSpeakingFrame are broadcast both upstream
    and downstream by transport.output(), so the validator (which is upstream of TTS)
    does see them.
"""

import re

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterimTranscriptionFrame,
    LLMMessagesAppendFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame

from app.game.state import SpellBeeGame


class SpellingValidator(FrameProcessor):
    """Judges spelling attempts against the current SpellBeeGame word.

    One attempt per word: once a valid spelling is extracted, the game advances,
    and no further transcriptions are judged until the bot finishes speaking the
    verdict (BotStoppedSpeakingFrame resets the verdict phase).
    """

    # Spoken letter-names that STT often transcribes as whole words, mapped to
    # the single letter they represent. Includes regional variants (e.g. zee/zed
    # for Z, aitch/haitch for H).
    _PHONETIC_LETTERS: dict[str, str] = {
        "ay": "a", "bee": "b", "see": "c", "sea": "c", "dee": "d", "ee": "e",
        "eff": "f", "gee": "g", "aitch": "h", "haitch": "h", "eye": "i",
        "jay": "j", "kay": "k", "el": "l", "ell": "l", "em": "m", "en": "n",
        "oh": "o", "owe": "o", "pee": "p", "cue": "q", "queue": "q", "ar": "r",
        "are": "r", "ess": "s", "tee": "t", "tea": "t", "you": "u", "yoo": "u",
        "vee": "v", "ex": "x", "why": "y", "zee": "z", "zed": "z",
    }

    # Minimum consecutive letter-like tokens to be considered a spelling attempt.
    # Matches the length of the shortest word in the game ("cat", "dog" = 3).
    # Raising this protects against isolated phonetic pronouns ("you"→u, "I"→i)
    # accidentally forming short strings in conversational sentences.
    _MIN_SPELLING_LETTERS: int = 3

    def __init__(self, game: SpellBeeGame, **kwargs):
        super().__init__(**kwargs)
        self._game = game
        # True while the bot's TTS audio is playing. Any transcription that
        # arrives during bot speech is an interruption or ambient echo — drop it.
        self._bot_is_speaking = False
        # True from the moment of judgment until bot speech ends. Prevents
        # Deepgram's segmented transcriptions from double-judging one spelling.
        self._awaiting_verdict = False

    # ------------------------------------------------------------------ #
    # Frame processing
    # ------------------------------------------------------------------ #

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_is_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_is_speaking = False
            self._awaiting_verdict = False
        elif isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)):
            self._log_stt(frame)
            if isinstance(frame, TranscriptionFrame) and not self._game.is_finished():
                await self._handle_transcription(frame, direction)
                return

        await self.push_frame(frame, direction)

    async def _handle_transcription(self, frame: TranscriptionFrame, direction: FrameDirection):
        """Route a final transcription: drop, pass to LLM, or judge as spelling."""
        if self._bot_is_speaking or self._awaiting_verdict:
            reason = "bot speaking" if self._bot_is_speaking else "verdict pending"
            logger.debug(f"[SpellingValidator] {reason}, dropping: '{frame.text}'")
            return

        guess = self._extract_spelling(frame.text)
        if not guess:
            logger.debug(f"[SpellingValidator] not a spelling attempt, passing: '{frame.text}'")
            await self.push_frame(frame, direction)
            return

        await self._judge(guess, direction)

    async def _judge(self, guess: str, direction: FrameDirection):
        """Record the result, advance the game, and emit verdict frames."""
        target = self._game.current_word()
        correct = guess == target

        logger.info(f"[SpellingValidator] word={target!r} guess={guess!r} correct={correct}")

        self._awaiting_verdict = True
        self._game.record_result(correct)
        self._game.advance()

        await self._push_game_state()
        await self._push_verdict(target, guess, correct)

    async def _push_game_state(self):
        """Send current game state to the browser via RTVI."""
        await self.push_frame(
            RTVIServerMessageFrame(
                data={
                    "type": "game_state",
                    "score": self._game.score,
                    "wordNumber": self._game.word_number,
                    "totalWords": self._game.total_words,
                    "finished": self._game.is_finished(),
                }
            ),
            FrameDirection.DOWNSTREAM,
        )

    async def _push_verdict(self, target: str, guess: str, correct: bool):
        """Inject the verdict instruction into the LLM context and trigger a response."""
        await self.push_frame(
            LLMMessagesAppendFrame(
                messages=[{"role": "system", "content": self._build_verdict(target, guess, correct)}],
                run_llm=True,
            ),
            FrameDirection.DOWNSTREAM,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _log_stt(frame: TranscriptionFrame | InterimTranscriptionFrame) -> None:
        label = "STT-final" if isinstance(frame, TranscriptionFrame) else "STT-interim"
        logger.info(f"[{label}] '{frame.text}'")

    def _extract_spelling(self, transcript: str) -> str:
        """Extract the letter-by-letter spelling from a transcript.

        Only CONSECUTIVE runs of letter-like tokens (single chars or phonetic
        letter-names) are considered. Whole words are skipped, so isolated
        pronouns like "I" or "you" that happen to be phonetic names for letters
        never form a valid spelling on their own.

        Returns the longest consecutive run if it is at least _MIN_SPELLING_LETTERS
        long; otherwise returns "".

        "a p p l e"                 -> "apple"
        "ay pee pee el ee"          -> "apple"
        "the spelling is a p p l e" -> "apple"  (preamble breaks before the run)
        "apple"                     -> ""       (whole word → skipped)
        "can you repeat the word again? I did not get it."
                                    -> ""       ('you'→u and 'I'→i are isolated)
        """
        tokens = re.split(r"[\s\-.,?!\'\"]+", transcript.lower().strip())

        best_run: list[str] = []
        current_run: list[str] = []

        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            if len(tok) == 1 and tok.isalpha():
                current_run.append(tok)
            elif tok in self._PHONETIC_LETTERS:
                current_run.append(self._PHONETIC_LETTERS[tok])
            else:
                if len(current_run) > len(best_run):
                    best_run = current_run
                current_run = []

        if len(current_run) > len(best_run):
            best_run = current_run

        result = "".join(best_run)
        return result if len(result) >= self._MIN_SPELLING_LETTERS else ""

    def _build_verdict(self, target: str, guess: str, correct: bool) -> str:
        """Build the system instruction sent to the LLM after each judgment.

        Called after record_result() and advance() so self._game reflects the
        new position (is_finished() and current_word() are already updated).
        """
        spaced = "-".join(target.upper())
        score = self._game.score
        total = self._game.total_words

        if self._game.is_finished():
            if correct:
                return (
                    f"The player spelled '{target}' correctly! "
                    f"The game is over. They scored {score} out of {total}. "
                    f"Celebrate enthusiastically and wrap up warmly."
                )
            return (
                f"The player spelled '{target}' incorrectly "
                f"(they said '{guess.upper()}', correct spelling is {spaced}). "
                f"The game is over. They scored {score} out of {total}. "
                f"Be encouraging and wrap up warmly."
            )

        next_word = self._game.current_word()
        if correct:
            return (
                f"The player spelled '{target}' correctly! "
                f"Congratulate them briefly, then present the next word: '{next_word}'. "
                f"Ask them to spell it out letter by letter."
            )
        return (
            f"The player spelled '{target}' incorrectly "
            f"(they said '{guess.upper()}', correct spelling is {spaced}). "
            f"Be kind, then present the next word: '{next_word}'. "
            f"Ask them to spell it out letter by letter."
        )
