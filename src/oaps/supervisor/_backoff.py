"""Exponential backoff calculator for service restarts.

This module provides a simple exponential backoff implementation with
jitter to prevent thundering herd problems when multiple services
restart simultaneously.
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExponentialBackoff:
    """Exponential backoff calculator with jitter.

    Computes delay durations for retry attempts using exponential backoff
    with optional random jitter to spread out restart attempts.

    The delay formula is:
        delay = min(base * (multiplier ^ attempt), max_delay)
        delay = delay * (1 - jitter/2 + random() * jitter)

    Attributes:
        base: Base delay in seconds for first retry.
        max_delay: Maximum delay in seconds.
        multiplier: Factor to multiply delay for each attempt.
        jitter: Fraction of delay to randomize (0.0-1.0).
    """

    base: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 0.1

    def delay(self, attempt: int) -> float:
        """Calculate the delay for a given attempt number.

        Args:
            attempt: The attempt number (0-indexed, where 0 is the first retry).

        Returns:
            The delay in seconds before the next retry attempt.
        """
        # Calculate base exponential delay
        exponential_delay = self.base * (self.multiplier**attempt)

        # Cap at max_delay
        capped_delay = min(exponential_delay, self.max_delay)

        # Apply jitter if configured
        if self.jitter > 0:
            # Add random jitter: delay * (1 +/- jitter/2)
            jitter_range = capped_delay * self.jitter
            jitter_offset = random.uniform(-jitter_range / 2, jitter_range / 2)  # noqa: S311
            capped_delay = max(0.0, capped_delay + jitter_offset)

        return capped_delay

    def reset_count(self) -> int:
        """Return the restart count that should reset backoff.

        After a service has been running successfully for a while,
        the restart count should be reset. This method returns the
        threshold for that reset.

        Returns:
            The restart count at which backoff should be considered reset.
        """
        return 0
