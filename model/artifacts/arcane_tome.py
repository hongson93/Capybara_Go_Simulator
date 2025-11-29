from model.core import BaseEffect, BattleState, HitContext, DamageType, compute_hit_damage


class ArcaneTomeEffect(BaseEffect):
    """
    Arcane Tome:

    Base version (level 1):
      - Every 4 bolts:
          deal 500% ATK as lightning skill damage (NOT a bolt).
      - Can trigger up to 3 times per round.

    Upgrade version (level 2):
      - Every 3 bolts:
          deal 750% ATK as lightning skill damage (NOT a bolt).
      - Can trigger up to 3 times per round.

    Counting rule:
      - Counts ANY bolt with tags including {"bolt", "lightning"}:
          * normal lightning bolts
          * Nashir thunder bolts
          * Ezra bolt (if tagged "bolt")
          * future bolt types
      - The Arcane Tome hit itself is NOT a bolt (no "bolt" tag).
      - Bolt count carries across rounds; only the number of procs per round is capped.
    """

    def __init__(self, adv_atk_mult: float, bolts_per_proc: int, coeff: float):
        """
        adv_atk_mult : adventurer's ATK multiplier (e.g. 1.15 for DG)
        bolts_per_proc : 4 (base) or 3 (upgrade)
        coeff : 5.0 (500%) or 7.5 (750%)
        """
        self.adv_atk_mult = adv_atk_mult
        self.bolts_per_proc = bolts_per_proc
        self.coeff = coeff

        self.max_procs_per_round = 3

        # Persistent bolt counter across rounds
        self.bolt_counter = 0

        # Per-round proc counter
        self.procs_this_round = 0

    def on_round_start(self, state: BattleState) -> None:
        # Only reset how many times we can proc this round.
        # DO NOT reset bolt_counter (we want overflow to carry over).
        self.procs_this_round = 0

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        # Only count real bolts (lightning + bolt)
        if "bolt" not in ctx.tags or "lightning" not in ctx.tags:
            return

        # Increment persistent bolt counter
        self.bolt_counter += 1

        # Consume bolts into procs, up to the per-round limit
        while (
            self.bolt_counter >= self.bolts_per_proc
            and self.procs_this_round < self.max_procs_per_round
        ):
            self.bolt_counter -= self.bolts_per_proc
            self.procs_this_round += 1

            # Fire Arcane Tome hit:
            # - skill + lightning (no "bolt" tag)
            # - uses current combo stacks as ATK buff
            atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

            tome_ctx = HitContext(
                damage_type=DamageType.OTHER_SKILL,
                coeff=self.coeff,  # 500% or 750%
                atk_mult_adventurer=self.adv_atk_mult,
                atk_mult_buff=atk_mult_buff,
                global_bonus=state.breath_global_this,
                tags={"skill", "lightning", "artifact"},
            )
            dmg = compute_hit_damage(tome_ctx, state)

            # Treat as generic skill damage in the breakdown
            state.dmg_other += dmg
