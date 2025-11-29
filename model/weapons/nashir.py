from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage, ATK_BASE, K_SKILL
import random  # if needed

class NashirScepterEffect(BaseEffect):
    """
    Nashir Scepter:
      - At end of each round: 1 lightning bolt (generic), 50% chance to convert to thunder.
      - Lightning base: 30% + 6% weapon => 36% coeff.
      - Thunder base: 90% + 6% weapon => 96% coeff.
      - Charge levels (additive to thunder coeff):
          lvl 1: +0.15
          lvl 2: +0.45
          lvl 3: +0.90
      - At lvl 3: release 6 thunder bolts, then reset to lvl 1.
      - Each thunder bolt (including converted and release) gives +20% bolt dmg,
        up to 9 stacks (integer stacks).
      - Bolts are LIGHTNING damage:
          * buffed by Breath's GLOBAL buff
          * NOT buffed by dragon_stacks S or breath_dragon_this.
    """
    def __init__(self, adv_atk_mult: float):
        self.adv_atk_mult = adv_atk_mult

        # Base coefficients with +6% flat from weapon
        self.base_lightning_coeff = 0.30 + 0.06   # 36%
        self.base_thunder_coeff   = 0.90 + 0.06   # 96%

        # Additive thunder bonuses per charge level
        self.thunder_bonus_by_level = {
            1: 0.15,                 # base +0.15
            2: 0.15 + 0.30,          # base +0.45
            3: 0.15 + 0.30 + 0.45,   # base +0.90
        }

        self.charge_level = 1
        self.bolt_stacks = 0.0
        self.max_bolt_stacks = 9.0

    def _rng(self, state: BattleState) -> random.Random:
        if state.rng is None:
            state.rng = random.Random()
        return state.rng

    def _global_bonus_common(self, state: BattleState) -> float:
        # Bolts see only global (Breath) buffs, not dragon-specific S
        return state.breath_global_this

    def _atk_buff_mult(self, state: BattleState) -> float:
        # Combo Mastery ATK buff (if present)
        return 1.0 + 0.10 * state.combo_stacks

    def _thunder_coeff(self) -> float:
        bonus = self.thunder_bonus_by_level[self.charge_level]
        return self.base_thunder_coeff + bonus

    def _bolt_mult(self) -> float:
        return 1.0 + 0.2 * min(self.bolt_stacks, self.max_bolt_stacks)

    def process_lightning_bolt(self, state: BattleState, atk_mult_buff: float, count: int = 1) -> None:
        """
        Process 'count' REAL lightning bolts:
          - Each bolt: rng 50% stays lightning, 50% becomes thunder
          - Each thunder bolt: +1 bolt stack (up to max)
        """
        if count <= 0:
            return

        rng = self._rng(state)
        global_bonus = self._global_bonus_common(state)

        for _ in range(count):
            is_thunder = rng.random() < 0.5
            if is_thunder:
                coeff = self._thunder_coeff()
            else:
                coeff = self.base_lightning_coeff

            bolt_ctx = HitContext(
                damage_type=DamageType.OTHER_SKILL,
                coeff=coeff,
                atk_mult_adventurer=self.adv_atk_mult,
                atk_mult_buff=atk_mult_buff,
                global_bonus=global_bonus,
                tags={"skill", "lightning", "bolt"}
            )
            dmg = compute_hit_damage(bolt_ctx, state)

            M_bolt = self._bolt_mult()
            state.dmg_bolt += dmg * M_bolt

            for e in state.effects:
                if hasattr(e, "on_after_bolt"):
                    e.on_after_bolt(state, bolt_ctx)

            if is_thunder:
                self.bolt_stacks = min(self.bolt_stacks + 1.0, self.max_bolt_stacks)

    def on_end_round_skills(self, state: BattleState) -> None:
        atk_mult_buff = self._atk_buff_mult(state)
        # weapon's own +1 bolt
        self.process_lightning_bolt(state, atk_mult_buff, count=1)


    def on_end_round_charge_release(self, state: BattleState) -> None:
        """
        Phase 4: charge release after everything else (Breath, per-round procs, buff expiry).
        Nashir: at charge level 3, release 6 thunder bolts and then reset to level 1.
        """
        atk_mult_buff = self._atk_buff_mult(state)
        global_bonus = self._global_bonus_common(state)

        if self.charge_level == 3:
            for _ in range(6):
                coeff = self._thunder_coeff()
                thunder_ctx = HitContext(
                    damage_type=DamageType.OTHER_SKILL,
                    coeff=coeff,
                    atk_mult_adventurer=self.adv_atk_mult,
                    atk_mult_buff=atk_mult_buff,
                    global_bonus=global_bonus,
                    tags={"skill", "lightning", "bolt"},
                )
                dmg_thunder = compute_hit_damage(thunder_ctx, state)
                M_bolt = self._bolt_mult()
                state.dmg_bolt += dmg_thunder * M_bolt

                # each real thunder bolt adds 1 stack
                self.bolt_stacks = min(self.bolt_stacks + 1.0, self.max_bolt_stacks)

        # Update charge level for next round:
        if self.charge_level < 3:
            self.charge_level += 1
        else:
            # after releasing at level 3, reset to level 1 for next round
            self.charge_level = 1

    # keep old on_round_end as no-op
    def on_round_end(self, state: BattleState) -> None:
        pass