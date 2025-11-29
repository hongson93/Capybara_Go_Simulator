from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage

class EzraRingEffect(BaseEffect):
    """
    Ezra Ring:
      - At the start of each round:
          * applies +final lightning damage (e.g. +20%) for this round
          * fires 1 'Ezra bolt':
                - 100% ATK as lightning damage
                - counts as a bolt (for Lightning Charge, Arcane Tome, etc.)
                - cannot convert, cannot be multiplied by Multiple Lightning
      - Buff ends at the 'buffs expire' phase of the same round.
    """
    def __init__(self, adv_atk_mult: float, final_light_bonus: float = 0.20):
        self.adv_atk_mult = adv_atk_mult
        self.final_light_bonus = final_light_bonus

    def on_round_start(self, state: BattleState) -> None:
        # Apply +final lightning for this round
        state.temp_final_lightning_bonus += self.final_light_bonus

        # Fire 1 Ezra bolt (special bolt, no conversion/multiplication)
        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        bolt_ctx = HitContext(
            damage_type=DamageType.OTHER_SKILL,
            coeff=1.0,  # 100% ATK
            atk_mult_adventurer=self.adv_atk_mult,
            atk_mult_buff=atk_mult_buff,
            global_bonus=state.breath_global_this,
            tags={"skill", "lightning", "bolt", "ezra"},  # <- IMPORTANT: "bolt"
        )
        if state.lightning_as_ninjutsu:
            bolt_ctx.tags.add("ninjutsu")
        dmg = compute_hit_damage(bolt_ctx, state)
        state.dmg_bolt += dmg  # or a dedicated non-bolt-lightning bucket if you add one

        # Lightning Charge & Arcane Tome will see this as a bolt because of the tags.
        # They are triggered in compute_hit_damage (Lightning Charge)
        # and via on_after_bolt notifications from bolt producers, if you decide to route Ezra through there.

    def on_end_round_buffs_expire(self, state: BattleState) -> None:
        # Remove the per-round final lightning buff
        state.temp_final_lightning_bonus = 0.0
