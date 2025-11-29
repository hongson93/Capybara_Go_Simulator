from model.core import BaseEffect, BattleState, HitContext

class ComboMasteryEffect(BaseEffect):
    """
    Each combo hit (not the first basic) gives +10% ATK,
    applied to subsequent hits. Stacks to 99 and never resets.
    """
    def __init__(self, atk_step: float = 0.10, max_stacks: int = 99):
        self.atk_step = atk_step
        self.max_stacks = max_stacks

    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None:
        ctx.atk_mult_buff *= (1.0 + self.atk_step * state.combo_stacks)

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        if ctx.is_combo:
            state.combo_stacks = min(state.combo_stacks + 1, self.max_stacks)
