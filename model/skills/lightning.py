from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage
from model.weapons.nashir import NashirScepterEffect
import random


class ExtraEndOfRoundBoltsEffect(BaseEffect):
    """
    At the end of every round, fire N generic lightning bolts.
    If Nashir is equipped, they go through Nashir.process_lightning_bolt
    (with conversion + stacks). Otherwise, plain lightning damage.

    multiple_lightning_factor is applied here by multiplying the number of
    normal lightning bolts BEFORE conversion.
    """
    def __init__(
        self,
        adv_atk_mult: float,
        n_bolts: int,
        nashir: NashirScepterEffect | None,
        multi_factor: int = 1,
    ):
        self.adv_atk_mult = adv_atk_mult
        self.n_bolts = n_bolts
        self.nashir = nashir
        self.multi_factor = multi_factor

    def on_end_round_skills(self, state: BattleState) -> None:
        if self.n_bolts <= 0:
            return

        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks
        total_bolts = self.n_bolts * self.multi_factor

        if self.nashir is not None:
            # Let Nashir handle conversion, stacks, +6% coeff, etc.
            self.nashir.process_lightning_bolt(state, atk_mult_buff, count=total_bolts)
        else:
            # Plain lightning: 30% coeff, no conversion, no bolt stacks
            for _ in range(total_bolts):
                tags = {"skill", "lightning", "bolt"}
                if state.lightning_as_ninjutsu:
                    tags.add("ninjutsu")
                if state.lightning_as_demonic:
                    tags.add("demonic")

                bolt_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=0.30 + state.daji_bolt_coeff_bonus,  # 30% lightning + Daji 4★ bonus
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    # breath_global_this and base_* bonuses are handled in compute_hit_damage
                    global_bonus=state.breath_global_this,
                    tags=tags,
                )
                dmg = compute_hit_damage(bolt_ctx, state)
                state.dmg_other += dmg

                for e in state.effects:
                    if hasattr(e, "on_after_bolt"):
                        e.on_after_bolt(state, bolt_ctx)


class BasicAttackBoltEffect(BaseEffect):
    """
    On-hit bolt skill:
      - Each basic/combo hit has 'chance' to trigger 2 lightning bolts (RNG).
      - Uses current Combo Mastery stacks (after that hit's increment).
      - multiple_lightning_factor multiplies the number of NORMAL lightning
        bolts before conversion.
    """
    def __init__(
        self,
        adv_atk_mult: float,
        chance: float,
        nashir: NashirScepterEffect | None,
        multi_factor: int = 1,
    ):
        self.adv_atk_mult = adv_atk_mult
        self.chance = chance  # 0.45 or 0.75, or boosted for Leo
        self.nashir = nashir
        self.multi_factor = multi_factor

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        if state.rng is None:
            state.rng = random.Random()
        rng = state.rng

        if rng.random() >= self.chance:
            return  # no proc

        n_bolts = 2 * self.multi_factor
        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        if self.nashir is not None:
            self.nashir.process_lightning_bolt(state, atk_mult_buff, count=n_bolts)
        else:
            for _ in range(n_bolts):
                tags = {"skill", "lightning", "bolt"}
                if state.lightning_as_ninjutsu:
                    tags.add("ninjutsu")
                if state.lightning_as_demonic:
                    tags.add("demonic")

                bolt_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=0.30 + state.daji_bolt_coeff_bonus,  # 30% lightning + Daji 4★ bonus
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    global_bonus=state.breath_global_this,
                    tags=tags,
                )
                dmg = compute_hit_damage(bolt_ctx, state)
                state.dmg_other += dmg

                for e in state.effects:
                    if hasattr(e, "on_after_bolt"):
                        e.on_after_bolt(state, bolt_ctx)


class FiveBoltsAfterRound6Effect(BaseEffect):
    """
    From round 6 onward, each end of round: fire 5 extra lightning bolts.
    Works like ExtraEndOfRoundBoltsEffect but starts at round >= 6.

    multiple_lightning_factor multiplies the number of NORMAL lightning bolts
    before conversion.
    """
    def __init__(
        self,
        adv_atk_mult: float,
        nashir: NashirScepterEffect | None,
        multi_factor: int = 1,
    ):
        self.adv_atk_mult = adv_atk_mult
        self.nashir = nashir
        self.n_bolts = 5
        self.multi_factor = multi_factor

    def on_end_round_skills(self, state: BattleState) -> None:
        if state.round_index < 6:
            return

        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks
        total_bolts = self.n_bolts * self.multi_factor

        if self.nashir is not None:
            self.nashir.process_lightning_bolt(state, atk_mult_buff, count=total_bolts)
        else:
            for _ in range(total_bolts):
                tags = {"skill", "lightning", "bolt"}
                if state.lightning_as_ninjutsu:
                    tags.add("ninjutsu")
                if state.lightning_as_demonic:
                    tags.add("demonic")

                bolt_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=0.30 + state.daji_bolt_coeff_bonus,  # 30% lightning + Daji 4★ bonus
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    global_bonus=state.breath_global_this,
                    tags=tags,
                )
                dmg = compute_hit_damage(bolt_ctx, state)
                state.dmg_other += dmg

                for e in state.effects:
                    if hasattr(e, "on_after_bolt"):
                        e.on_after_bolt(state, bolt_ctx)