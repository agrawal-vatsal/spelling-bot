"""Custom frame processor: validates a single spelling attempt.

This is the heart of the assignment — the "custom frame processor" requirement.

Design (Option A: code judges, LLM emotes):
  * CODE owns the target word (passed in at construction). The LLM never picks
    the word and never decides correctness — it is purely the excited host voice.
  * The processor sits right after STT. It watches for the user's FINAL speech
    transcription, normalizes it into a plain letter string, and compares it to
    the target word.
  * It then injects a system message telling the host LLM the verdict and to
    react + end the game. `run_llm=True` makes the bot actually speak that
    reaction.
  * Single round: after the first judged attempt, `_answered` flips to True and
    further speech is ignored.

Why normalize? STT does not return clean letters. Someone spelling "apple" out
loud can transcribe as "a p p l e", "ay pee pee el ee", "A-P-P-L-E", or even
"apple" if said fast. normalize_spelling() collapses all of those to "apple".
"""

import re

from loguru import logger

from pipecat.frames.frames import Frame, TranscriptionFrame, LLMMessagesAppendFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection


# Spoken letter-names that STT often transcribes as whole words, mapped back
# to the single letter they represent.
PHONETIC_LETTERS = {
    "ay": "a", "bee": "b", "see": "c", "sea": "c", "dee": "d", "ee": "e",
    "eff": "f", "gee": "g", "aitch": "h", "haitch": "h", "eye": "i",
    "jay": "j", "kay": "k", "el": "l", "ell": "l", "em": "m", "en": "n",
    "oh": "o", "owe": "o", "pee": "p", "cue": "q", "queue": "q", "ar": "r",
    "are": "r", "ess": "s", "tee": "t", "tea": "t", "you": "u", "yoo": "u",
    "vee": "v", "ex": "x", "why": "y", "zee": "z", "zed": "z",
}


def normalize_spelling(transcript: str) -> str:
    """Convert a spoken-spelling transcript into a bare lowercase letter string.

    "A-P-P-L-E"        -> "apple"
    "a p p l e"        -> "apple"
    "ay pee pee el ee" -> "apple"
    "it's apple"       -> "apple"   (they just said the word)
    """
    text = transcript.lower().strip()
    tokens = re.split(r"[\s\-.,]+", text)

    letters = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if len(tok) == 1 and tok.isalpha():
            letters.append(tok)
        elif tok in PHONETIC_LETTERS:
            letters.append(PHONETIC_LETTERS[tok])
        elif tok.isalpha():
            # A whole word slipped through; treat its characters as the spelling.
            letters.extend(list(tok))
    return "".join(letters)


class SpellingValidator(FrameProcessor):
    """Judges one spelling attempt for `target_word`, then ends the round."""

    def __init__(self, target_word: str, **kwargs):
        super().__init__(**kwargs)
        self._target = target_word.lower()
        self._answered = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Only act on the user's FINAL transcription, and only once.
        is_attempt = (
            isinstance(frame, TranscriptionFrame)
            and getattr(frame, "finalized", True)
            and not self._answered
        )

        if not is_attempt:
            await self.push_frame(frame, direction)
            return

        guess = normalize_spelling(frame.text)

        # Empty/garbled guess: let it pass so the host can ask them to try again,
        # and do NOT mark the round answered.
        if not guess:
            logger.debug(f"[SpellingValidator] empty guess from '{frame.text}'")
            await self.push_frame(frame, direction)
            return

        correct = guess == self._target
        spaced = "-".join(self._target.upper())
        logger.info(
            f"[SpellingValidator] target='{self._target}' guess='{guess}' "
            f"correct={correct}"
        )

        if correct:
            verdict = (
                f"The player spelled '{self._target}' correctly. "
                "Congratulate them enthusiastically, then warmly end the game."
            )
        else:
            verdict = (
                f"The player spelled '{self._target}' incorrectly "
                f"(they said '{guess.upper()}'). Kindly tell them the correct "
                f"spelling is {spaced}, encourage them, then warmly end the game."
            )

        self._answered = True

        # Inject the verdict as a system instruction and trigger the bot to speak.
        # We CONSUME the original transcription (do not push it) so the raw
        # letters don't separately drive the LLM — this injected message is the
        # single, code-controlled trigger for the bot's reaction.
        await self.push_frame(
            LLMMessagesAppendFrame(
                messages=[{"role": "system", "content": verdict}],
                run_llm=True,
            ),
            FrameDirection.DOWNSTREAM,
        )
