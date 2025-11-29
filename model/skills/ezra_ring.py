from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage

class EzraRingEffect(BaseEffect):
    """
    Ezra Ring:
      - At the start of each round:
          * applies +final lightning damage (e.g. +20%) for this round
          * fires 1 'Ezra bolt':
                - 100% ATK as lightning damage
                - cannot convert / multiply
                - still counts as a 'bolt' for Lightning Charge, etc.
      - Buff ends at the 'buffs expire' phase of the same round.
    """
    def __init__(self, adv_atk_mult: float, final_light_bonus: float = 0.20):
        self.adv_atk_mult = adv_atk_mult
        self.final_light_bonus = final_light_bonus

    def on_round_start(self, state: BattleState) -> None:
        # Apply +final lightning for this round
        state.temp_final_lightning_bonus += self.final_light_bonus

        # Fire 1 Ezra bolt (100% ATK lightning, special, no conversion/multiplication)
        # Uses current combo stacks as ATK buff, just like other skills.
        atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

        bolt_ctx = HitContext(
            damage_type=DamageType.OTHER_SKILL,
            coeff=1.0,  # 100% ATK
            atk_mult_adventurer=self.adv_atk_mult,
            atk_mult_buff=atk_mult_buff,
            global_bonus=state.breath_global_this,  # global buffs still apply
            tags={"skill", "lightning", "bolt", "ezra"},
        )
        dmg = compute_hit_damage(bolt_ctx, state)
        state.dmg_other += dmg  # treat as generic skill damage in breakdown

    def on_end_round_buffs_expire(self, state: BattleState) -> None:
        # Remove the per-round final lightning buff
        state.temp_final_lightning_bonus = 0.0
