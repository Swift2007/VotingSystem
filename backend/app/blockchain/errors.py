"""Exceptions raised by the simulated blockchain."""


class ChainError(Exception):
    """Base class for blockchain errors."""


class InvalidBlockError(ChainError):
    """A block failed validation (bad link, hash, PoW, merkle root, ...)."""


class ConsensusError(ChainError):
    """Fewer than a majority of nodes accepted a proposed block."""


class ChainIntegrityError(ChainError):
    """The canonical chain failed validation, so tallying is refused."""


class ChainFinalizedError(ChainError):
    """A block was proposed after the results block closed the chain."""
