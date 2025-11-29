from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage
import random


class LeoMultiHitNinjutsuEffect(BaseEffect):
    """
    Leo basic/combo conversion:

    0★:
      - Each basic/combo is converted into 3 hits:
          30%, 70%, 100% (total 200%) as BASIC damage.
      - After those 3 hits, always proc 1 ninjutsu hit:
          100% ATK as ninjutsu skill damage.

    2★:
      - Additionally, each of the 3 hits has a 70% chance
        to proc an extra ninjutsu hit with the SAME coefficient
        (30 / 70 / 100%).
      - Those ninjutsu hits also carry the "basic" tag
        for synergy with basic-related effects.

    Implementation:
      - We set the original basic hit's coeff to 0 (no direct damage).
      - Then, in on_after_hit, we manually create the 3 basic sub-hits
        + ninjutsu procs.
    """
    def __init__(self, adv_atk_mult: float, has_2star: bool):
        self.adv_atk_mult = adv_atk_mult
        self.has_2star = has_2star

    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None:
        # Only intercept BASIC hits (Leo is the adventurer, so all basics are his)
        if ctx.damage_type == DamageType.BASIC:
            # Cancel the original basic damage; we will handle it ourselves
            ctx.coeff = 0.0

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        if ctx.damage_type != DamageType.BASIC:
            return

        # Ensure RNG exists
        if state.rng is None:
            state.rng = random.Random()
        rng = state.rng

        # Three-part basic: 30%, 70%, 100% = total 200%
        basic_parts = [0.30, 0.70, 1.00]

        for part_coeff in basic_parts:
            # BASIC sub-hit
            basic_ctx = HitContext(
                damage_type=DamageType.BASIC,
                coeff=part_coeff,
                is_basic=ctx.is_basic,
                is_combo=ctx.is_combo,
                hit_index_in_round=ctx.hit_index_in_round,
                atk_base=ctx.atk_base,
                atk_mult_adventurer=self.adv_atk_mult,
                atk_mult_buff=ctx.atk_mult_buff,
                global_bonus=ctx.global_bonus,
                tags={"basic"},
            )
            dmg_basic = compute_hit_damage(basic_ctx, state)
            state.dmg_basic += dmg_basic

            # 2★: 70% chance to proc ninjutsu of same coeff
            if self.has_2star:
                if rng.random() < 0.70:
                    ninj_ctx = HitContext(
                        damage_type=DamageType.OTHER_SKILL,
                        coeff=part_coeff,
                        atk_base=ctx.atk_base,
                        atk_mult_adventurer=self.adv_atk_mult,
                        atk_mult_buff=ctx.atk_mult_buff,
                        global_bonus=ctx.global_bonus,
                        tags={"skill", "ninjutsu", "basic"},
                    )
                    dmg_ninj = compute_hit_damage(ninj_ctx, state)
                    state.dmg_other += dmg_ninj

        # 0★/2★: after the 3 hits, always 1× 100% ninjutsu
        ninj_final_ctx = HitContext(
            damage_type=DamageType.OTHER_SKILL,
            coeff=1.0,
            atk_base=ctx.atk_base,
            atk_mult_adventurer=self.adv_atk_mult,
            atk_mult_buff=ctx.atk_mult_buff,
            global_bonus=ctx.global_bonus,
            tags={"skill", "ninjutsu"},
        )
        dmg_final = compute_hit_damage(ninj_final_ctx, state)
        state.dmg_other += dmg_final


class LeoHurricaneEffect(BaseEffect):
    """
    Leo's 'Hurricane' skill (4★ / 7★):

    4★:
      - Starting from round 2, every 3 rounds (2, 5, 8, ...)
      - Hurricane: 5 hits × 200% ATK ninjutsu damage.

    7★:
      - Starting from round 1, every 2 rounds (1, 3, 5, ...)
      - Hurricane: 5 hits × 400% ATK ninjutsu damage.
    """
    def __init__(self, adv_atk_mult: float, start_round: int, interval: int, coeff: float):
        self.adv_atk_mult = adv_atk_mult
        self.start_round = start_round
        self.interval = interval
        self.coeff = coeff  # 2.0 or 4.0 (200% or 400%)

    def on_end_round_adventurer(self, state: BattleState) -> None:
        r = state.round_index
        if r < self.start_round:
            return
        if (r - self.start_round) % self.interval != 0:
            return

        # Hurricane: 5 ninjutsu hits
        for _ in range(5):
            ctx = HitContext(
                damage_type=DamageType.OTHER_SKILL,
                coeff=self.coeff,
                atk_mult_adventurer=self.adv_atk_mult,
                global_bonus=state.breath_global_this,  # global buffs
                tags={"skill", "ninjutsu"},
            )
            dmg = compute_hit_damage(ctx, state)
            state.dmg_other += dmg


class LeoLightningNinjutsuFlagEffect(BaseEffect):
    """
    Leo 5★:
      - Allow lightning to gain ninjutsu bonus:
        all lightning hits also have 'ninjutsu' tag.

      This effect simply sets a flag on the BattleState; the actual
      lightning-producing code (Nashir, Ezra, generic lightning skills, etc.)
      should check state.lightning_as_ninjutsu and add 'ninjutsu' to tags.
    """
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def on_round_start(self, state: BattleState) -> None:
        state.lightning_as_ninjutsu = self.enabled


class LeoChargeReleaseNinjutsuEffect(BaseEffect):
    """
    Leo 8★ / 10★: extra ninjutsu on charge release.

    8★:
      - On Nashir charge release (6 bolts), before the bolts:
        trigger 3 hits × 300% ATK ninjutsu damage.

    10★:
      - Upgrade 8★:
          * 3 hits × 500% ATK ninjutsu damage
          * additionally, buff GLOBAL ninjutsu damage by 60% (0.6)
            once, permanent until end of battle (no stacking).
    """
    def __init__(self, adv_atk_mult: float, coeff: float, grant_global_ninjutsu: bool):
        self.adv_atk_mult = adv_atk_mult
        self.coeff = coeff      # 3.0 or 5.0
        self.grant_global_ninjutsu = grant_global_ninjutsu
        self.global_buff_applied = False

    def on_before_charge_release(self, state: BattleState) -> None:
        # Extra ninjutsu hits before the 6 bolts
        for _ in range(3):
            ctx = HitContext(
                damage_type=DamageType.OTHER_SKILL,
                coeff=self.coeff,
                atk_mult_adventurer=self.adv_atk_mult,
                global_bonus=state.breath_global_this,
                tags={"skill", "ninjutsu"},
            )
            dmg = compute_hit_damage(ctx, state)
            state.dmg_other += dmg

        # Leo 10★: one-time +60% global ninjutsu
        if self.grant_global_ninjutsu and not self.global_buff_applied:
            state.dynamic_global_ninjutsu_bonus += 0.60
            self.global_buff_applied = True


def leo_effects_for_star(star: int, with_combo_mastery: bool) -> list[BaseEffect]:
    """
    Build Leo's effect list for a given star level.
    - combo_mastery is handled in core/build_effects_from_config,
      like for Dragon Girl; this function only cares about Leo-specific stuff.
    """
    effects: list[BaseEffect] = []

    adv_atk_mult = 1.10  # Leo's ATK multiplier

    # 0★ / 2★: multi-hit basic + ninjutsu
    has_2star = star >= 2
    effects.append(LeoMultiHitNinjutsuEffect(adv_atk_mult=adv_atk_mult, has_2star=has_2star))

    # 4★ / 7★: Hurricane
    if 4 <= star <= 6:
        # from round 2, every 3 rounds, 5×200% ninjutsu
        effects.append(LeoHurricaneEffect(
            adv_atk_mult=adv_atk_mult,
            start_round=2,
            interval=3,
            coeff=2.0,
        ))
    elif star >= 7:
        # from round 1, every 2 rounds, 5×400% ninjutsu
        effects.append(LeoHurricaneEffect(
            adv_atk_mult=adv_atk_mult,
            start_round=1,
            interval=2,
            coeff=4.0,
        ))

    # 5★: lightning gains 'ninjutsu' tag
    effects.append(LeoLightningNinjutsuFlagEffect(enabled=(star >= 5)))

    # 8★ / 10★: charge-release ninjutsu
    if 8 <= star <= 9:
        # 3×300% ninjutsu on each charge release
        effects.append(LeoChargeReleaseNinjutsuEffect(
            adv_atk_mult=adv_atk_mult,
            coeff=3.0,
            grant_global_ninjutsu=False,
        ))
    elif star >= 10:
        # 3×500% ninjutsu + one-time +60% global ninjutsu
        effects.append(LeoChargeReleaseNinjutsuEffect(
            adv_atk_mult=adv_atk_mult,
            coeff=5.0,
            grant_global_ninjutsu=True,
        ))

    return effects

