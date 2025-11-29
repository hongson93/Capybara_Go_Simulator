from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage
from model.weapons.nashir import NashirScepterEffect
import random


class ExtraEndOfRoundBoltsEffect(BaseEffect):
    """
    At the end of every round, fire N generic lightning bolts.
    If Nashir is equipped, they go through Nashir.process_lightning_bolt
    (with conversion + stacks). Otherwise, plain lightning damage.
    """
    def __init__(self, adv_atk_mult: float, n_bolts: int, nashir: NashirScepterEffect | None):
        self.adv_atk_mult = adv_atk_mult
        self.n_bolts = n_bolts
        self.nashir = nashir

    def on_end_round_skills(self, state: BattleState) -> None:
        if self.n_bolts <= 0:
            return

        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        if self.nashir is not None:
            # Let Nashir handle conversion, stacks, +6% coeff, etc.
            self.nashir.process_lightning_bolt(state, atk_mult_buff, count=self.n_bolts)
        else:
            # Plain lightning: 30% coeff, no conversion, no bolt stacks
            for _ in range(self.n_bolts):
                bolt_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=0.30,  # 30% lightning
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    # breath_global_this and base_* bonuses are handled in compute_hit_damage
                    global_bonus=state.breath_global_this,
                    tags={"skill", "lightning"},
                )
                dmg = compute_hit_damage(bolt_ctx, state)
                state.dmg_other += dmg


class BasicAttackBoltEffect(BaseEffect):
    """
    On-hit bolt skill:
      - Each basic/combo hit has 'chance' to trigger 2 lightning bolts (RNG).
      - Uses current Combo Mastery stacks (after that hit's increment).
    """
    def __init__(self, adv_atk_mult: float, chance: float, nashir: NashirScepterEffect | None):
        self.adv_atk_mult = adv_atk_mult
        self.chance = chance  # 0.45 or 0.80
        self.nashir = nashir

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        if state.rng is None:
            state.rng = random.Random()
        rng = state.rng

        if rng.random() >= self.chance:
            return  # no proc

        n_bolts = 2
        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        if self.nashir is not None:
            self.nashir.process_lightning_bolt(state, atk_mult_buff, count=n_bolts)
        else:
            for _ in range(n_bolts):
                bolt_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=0.30,
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    global_bonus=state.breath_global_this,
                    tags={"skill", "lightning"},
                )
                dmg = compute_hit_damage(bolt_ctx, state)
                state.dmg_other += dmg


class FiveBoltsAfterRound6Effect(BaseEffect):
    """
    From round 6 onward, each end of round: fire 5 extra lightning bolts.
    Works like ExtraEndOfRoundBoltsEffect but starts at round >= 6.
    """
    def __init__(self, adv_atk_mult: float, nashir: NashirScepterEffect | None):
        self.adv_atk_mult = adv_atk_mult
        self.nashir = nashir
        self.n_bolts = 5

    def on_end_round_skills(self, state: BattleState) -> None:
        if state.round_index < 6:
            return

        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        if self.nashir is not None:
            self.nashir.process_lightning_bolt(state, atk_mult_buff, count=self.n_bolts)
        else:
            for _ in range(self.n_bolts):
                bolt_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=0.30,
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    global_bonus=state.breath_global_this,
                    tags={"skill", "lightning"},
                )
                dmg = compute_hit_damage(bolt_ctx, state)
                state.dmg_other += dmg
