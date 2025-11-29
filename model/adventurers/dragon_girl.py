from typing import List
from model.core import (
    BaseEffect,
    BattleState,
    HitContext,
    DamageType,
    compute_hit_damage,
)
from model.skills.combo_mastery import ComboMasteryEffect


class DGDragonStacksEffect(BaseEffect):
    """
    From 5★ onwards:
    - +1 stack at start of round
    - +1 stack after every hit
    - each stack gives +5% 'dragon flame global' that applies to:
        - basic attacks
        - dragon flame hits
        - dragon breath
      but NOT to lightning/thunder bolts, etc.
    """
    def __init__(self, enabled: bool, stack_step: float = 0.05, max_stacks: int = 20):
        self.enabled = enabled
        self.stack_step = stack_step
        self.max_stacks = max_stacks

    def on_round_start(self, state: BattleState) -> None:
        if not self.enabled:
            return
        state.dragon_stacks = min(state.dragon_stacks + 1, self.max_stacks)

    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None:
        if not self.enabled:
            return

        if ctx.damage_type in (
            DamageType.BASIC,
            DamageType.DRAGON_FLAME,
            DamageType.DRAGON_BREATH,
        ):
            S = self.stack_step * state.dragon_stacks
            ctx.global_bonus += S

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        if not self.enabled:
            return
        state.dragon_stacks = min(state.dragon_stacks + 1, self.max_stacks)


class DGDragonFlameOnHitEffect(BaseEffect):
    """
    Every basic/combo hit triggers one dragon flame hit
    with star-dependent coefficient. On-hit damage benefits
    from the latest Combo Mastery stacks (including this combo).
    """
    def __init__(self, coeff: float):
        self.coeff = coeff

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        # Recompute ATK buff from current combo_stacks (after ComboMasteryEffect.on_after_hit)
        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        flame_ctx = HitContext(
            damage_type=DamageType.DRAGON_FLAME,
            coeff=self.coeff,
            is_basic=False,
            is_combo=False,
            hit_index_in_round=ctx.hit_index_in_round,
            atk_base=ctx.atk_base,
            atk_mult_adventurer=ctx.atk_mult_adventurer,
            atk_mult_buff=atk_mult_buff,
            # stacks + breath_global already in ctx.global_bonus;
            # add breath_dragon_this for flame
            global_bonus=ctx.global_bonus + state.breath_dragon_this,
            tags={"skill", "dragon_flame"},
        )
        dmg = compute_hit_damage(flame_ctx, state)
        state.dmg_flame += dmg


class DGDragonBreathEffect(BaseEffect):
    """
    Dragon Breath:
      - Triggers on odd rounds (1,3,5,...).
      - Deals dragon-flame damage.
      - Grants:
          * dragon-only bonus (breath_dragon_next)
          * global bonus (breath_global_next on 8★+)
        that apply:
          * immediately to any later end-of-round effects
          * and for the whole next round.
    """
    def __init__(
        self,
        enabled: bool,
        coeff: float,
        dragon_bonus_next: float,
        global_bonus_next: float,
    ):
        self.enabled = enabled
        self.coeff = coeff
        self.dragon_bonus_next = dragon_bonus_next
        self.global_bonus_next = global_bonus_next

    def on_round_start(self, state: BattleState) -> None:
        # Apply buffs that were scheduled from the previous round
        state.breath_global_this = state.breath_global_next
        state.breath_dragon_this = state.breath_dragon_next
        state.breath_global_next = 0.0
        state.breath_dragon_next = 0.0

    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None:
        # Breath's GLOBAL buff applies to all hits
        ctx.global_bonus += state.breath_global_this

    def on_end_round_adventurer(self, state: BattleState) -> None:
        if not self.enabled:
            return
        if state.round_index % 2 == 0:
            return  # only odd rounds

        # Dragon Breath is dragon-flame damage:
        S = 0.05 * state.dragon_stacks  # 0 if stacks not enabled
        global_bonus = state.breath_global_this + state.breath_dragon_this + S

        breath_ctx = HitContext(
            damage_type=DamageType.DRAGON_BREATH,
            coeff=self.coeff,
            atk_mult_adventurer=1.15,  # DG's ATK multiplier
            global_bonus=global_bonus,
            tags={"skill", "dragon_flame"},
        )
        dmg = compute_hit_damage(breath_ctx, state)
        state.dmg_breath += dmg

        # Schedule buffs for the NEXT round...
        state.breath_dragon_next += self.dragon_bonus_next
        state.breath_global_next += self.global_bonus_next

        # ...and ALSO make them active for any later end-of-round effects THIS round
        state.breath_dragon_this += self.dragon_bonus_next
        state.breath_global_this += self.global_bonus_next

    def on_round_end(self, state: BattleState) -> None:
        # no-op, end-of-round handled by on_end_round_adventurer
        pass


def dg_effects_for_star(star: int, with_combo_mastery: bool) -> List[BaseEffect]:
    """
    Build the list of DG-related effects for a given star and combo mastery flag.
    """
    effects: List[BaseEffect] = []

    if with_combo_mastery:
        effects.append(ComboMasteryEffect())

    has_stacks = star >= 5
    effects.append(DGDragonStacksEffect(enabled=has_stacks))

    flame_coeff = 0.9 if star < 2 else 1.8
    effects.append(DGDragonFlameOnHitEffect(coeff=flame_coeff))

    if star < 4:
        effects.append(DGDragonBreathEffect(False, 0.0, 0.0, 0.0))
    elif 4 <= star <= 6:
        effects.append(DGDragonBreathEffect(
            True,
            coeff=6.0,
            dragon_bonus_next=0.3,
            global_bonus_next=0.0,
        ))
    elif star == 7:
        effects.append(DGDragonBreathEffect(
            True,
            coeff=12.0,
            dragon_bonus_next=0.6,
            global_bonus_next=0.0,
        ))
    else:  # 8, 9, 10
        effects.append(DGDragonBreathEffect(
            True,
            coeff=12.0,
            dragon_bonus_next=0.6,
            global_bonus_next=0.3,
        ))

    return effects
