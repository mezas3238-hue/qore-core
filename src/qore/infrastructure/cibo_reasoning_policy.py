from __future__ import annotations

from dataclasses import dataclass

from qore.kernel.errors import InfrastructureError
from qore.modules.cibo.cognitive_contracts import CiboReasoningMode


class CiboReasoningPolicyError(InfrastructureError):
    """A reasoning-routing situation violated the governed policy contract."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class CiboReasoningSituation:
    """Explicit signals used to route CIBO reasoning depth without text heuristics."""

    serious_controversy: bool = False
    adversarial_council: bool = False

    def __post_init__(self) -> None:
        if type(self.serious_controversy) is not bool:
            raise CiboReasoningPolicyError("serious_controversy must be exact bool")
        if type(self.adversarial_council) is not bool:
            raise CiboReasoningPolicyError("adversarial_council must be exact bool")


def select_cibo_reasoning_mode(
    situation: CiboReasoningSituation,
) -> CiboReasoningMode:
    """HIGH normally; MAX for material controversy; adversarial council above MAX."""
    if type(situation) is not CiboReasoningSituation:
        raise CiboReasoningPolicyError("reasoning situation must be exact CiboReasoningSituation")
    situation.__post_init__()
    if situation.adversarial_council:
        return CiboReasoningMode.COUNCIL_ADVERSARIAL
    if situation.serious_controversy:
        return CiboReasoningMode.MAX
    return CiboReasoningMode.HIGH
