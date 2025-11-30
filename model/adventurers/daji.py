from typing import List
from model.core import (
    BaseEffect,
    BattleState,
    HitContext,
    DamageType,
    compute_hit_damage,
)


class DajiFormEffect(BaseEffect):
    """
    Handles Daji's Demonic Aura stacks, Queen/Fox form, Fox Flame,
    Fox-form bolt buff, lightning-as-demonic, and 10★ global Demonic Aura buff.

    Star effects implemented:

    0★:
      - At end of each round, gain 3 stacks of Demonic Aura (max 9).
      - When reaching 9 stacks, immediately transform into Fox Form for 1 round.
        * Transform happens after buff-expire phase, before charge release.
      - When Fox Form ends, Demonic Aura stacks reset to 0.
      - In Fox Form, the first skill (here: Fox Flame) deals an *extra*
        1100% ATK as Demonic Aura damage.

    4★:
      - Whenever transforming into Fox Form, immediately activate Fox Flame:
          1200% ATK as Demonic Aura damage.
      - While in Fox Form, all bolts (Ezra, Nashir, generic lightning) get
        +60% coefficient (we implement it as a 1.6× coeff multiplier).

    5★:
      - At the start of round 1, gain 9 stacks and immediately transform.
      - This initial transform lasts only until the end of round 1.
      - While in Fox Form, lightning skills (artifact and all bolts) gain
        Demonic Aura tag ("demonic"), so they benefit from demonic-aura buffs.

    7★:
      - Upgrade Fox Flame to 3600% ATK Demonic Aura damage.

    10★:
      - Gain +60% *global* Demonic Aura damage for the entire battle.
        This applies to all hits tagged with "demonic", including:
          * Demonic Aura skills (0★ extra hit, Fox Flame, ultimate)
          * Lightning skills in Fox Form (5★ effect).
    """

    def __init__(self, adv_atk_mult: float, star: int):
        self.adv_atk_mult = adv_atk_mult
        self.star = star
        self.initial_fox_applied = False
        self.global_demonic_applied = False

    # ---------------------------
    # Helpers
    # ---------------------------

    def _enter_fox_form(self, state: BattleState, expire_after_round: int) -> None:
        if state.daji_fox_form_active:
            return

        state.daji_fox_form_active = True
        state.daji_fox_form_expires_after_round = expire_after_round

        # 5★: lightning skills in Fox Form gain Demonic Aura tag
        if self.star >= 5:
            state.lightning_as_demonic = True

        # 0★: On entering Fox Form, deal 1100% Demonic Aura as the “first skill”
        extra_ctx = HitContext(
            damage_type=DamageType.DEMONIC_AURA,
            coeff=11.0,  # 1100%
            atk_mult_adventurer=self.adv_atk_mult,
            global_bonus=state.breath_global_this,
            tags={"skill", "demonic"},
        )
        dmg_extra = compute_hit_damage(extra_ctx, state)
        state.dmg_demonic += dmg_extra

        # 4★ / 7★: Fox Flame on transform
        if self.star >= 4:
            coeff = 12.0 if self.star < 7 else 36.0

            flame_ctx = HitContext(
                damage_type=DamageType.FLAME_FOX,
                coeff=coeff,
                atk_mult_adventurer=self.adv_atk_mult,
                global_bonus=state.breath_global_this,
                tags={"skill", "demonic"},
            )
            dmg_flame = compute_hit_damage(flame_ctx, state)
            state.dmg_fox_flame += dmg_flame

    def _leave_fox_form(self, state: BattleState) -> None:
        """
        Return to Queen Form and reset aura stacks and Fox-specific flags.
        """
        if not state.daji_fox_form_active:
            return

        state.daji_fox_form_active = False
        state.daji_fox_form_expires_after_round = 0
        state.daji_fox_first_skill_pending = False

        # Demonic Aura stacks reset when Fox Form ends
        state.daji_aura_stacks = 0

        # 5★: lightning-as-demonic only during Fox Form
        state.lightning_as_demonic = False

    # ---------------------------
    # Battle lifecycle hooks
    # ---------------------------

    def on_round_start(self, state: BattleState) -> None:
        # 10★: one-time +60% global Demonic Aura damage at battle start
        if self.star >= 10 and not self.global_demonic_applied:
            state.dynamic_global_demonic_bonus += 0.60
            self.global_demonic_applied = True

        # 5★: at start of round 1, immediately transform with 9 stacks.
        if self.star >= 5 and state.round_index == 1 and not self.initial_fox_applied:
            state.daji_aura_stacks = 9
            self._enter_fox_form(state, expire_after_round=1)
            self.initial_fox_applied = True

    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None:
        # 4★: While in Fox Form, buff all bolt coefficients by +60%.
        if self.star >= 4 and state.daji_fox_form_active and "bolt" in ctx.tags:
            ctx.coeff += 0.6

    def on_end_round_buffs_expire(self, state: BattleState) -> None:
        """
        End-of-round logic:
          1) Handle Fox Form expiry.
          2) If not in Fox Form, gain +3 Demonic Aura stacks (max 9).
             On reaching 9, transform into Fox Form for 1 full *next* round.
        """
        # 1) Fox Form expiry
        if state.daji_fox_form_active and state.round_index >= state.daji_fox_form_expires_after_round:
            self._leave_fox_form(state)

        # 2) Aura stacks & transform (0★ effect)
        if not state.daji_fox_form_active:
            # Gain 3 stacks per round, up to 9
            state.daji_aura_stacks = min(state.daji_aura_stacks + 3, 9)

            # On reaching 9 stacks, transform for 1 full next round:
            # this call happens after buff expiry but before charge release, as required.
            if state.daji_aura_stacks >= 9:
                expire_after = state.round_index + 1
                self._enter_fox_form(state, expire_after_round=expire_after)


class DajiChargeReleaseUltimateEffect(BaseEffect):
    """
    8★: On charge release (Nashir level 3), before the 6 bolts:
         - Deal 900% ATK as Demonic Aura damage (one hit).
    The hit always has the "demonic" tag so it benefits from 10★ global
    Demonic Aura buff if present.
    """

    def __init__(self, adv_atk_mult: float):
        self.adv_atk_mult = adv_atk_mult

    def on_before_charge_release(self, state: BattleState) -> None:
        ctx = HitContext(
            damage_type=DamageType.ULTIMATE,
            coeff=9.0,  # 900%
            atk_mult_adventurer=self.adv_atk_mult,
            global_bonus=state.breath_global_this,
            tags={"skill", "demonic"},
        )
        dmg = compute_hit_damage(ctx, state)
        state.dmg_ultimate += dmg


def daji_effects_for_star(star: int, with_combo_mastery: bool) -> List[BaseEffect]:
    """
    Build Daji's effect list for a given star level.
    Combo Mastery itself is handled in core/build_effects_from_config;
    this function only cares about Daji-specific behaviour.
    """
    effects: List[BaseEffect] = []

    adv_atk_mult = 1.15  # same as Dragon Girl for now

    # Core Daji form / aura logic (0★, 4★, 5★, 7★, 10★)
    effects.append(DajiFormEffect(adv_atk_mult=adv_atk_mult, star=star))

    # 8★: Demonic Aura ultimate on charge release
    if star >= 8:
        effects.append(DajiChargeReleaseUltimateEffect(adv_atk_mult=adv_atk_mult))

    return effects
