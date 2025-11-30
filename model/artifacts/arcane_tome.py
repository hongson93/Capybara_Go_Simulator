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
      - Counts ANY bolt with tags including {"bolt", "lightning"}.
      - Tome hit itself is NOT a bolt (no 'bolt' tag).
      - Bolt count carries across rounds; only procs per round are capped.
    """

    def __init__(self, adv_atk_mult: float, bolts_per_proc: int, coeff: float):
        self.adv_atk_mult = adv_atk_mult
        self.bolts_per_proc = bolts_per_proc
        self.coeff = coeff

        self.max_procs_per_round = 3

        # Persistent bolt counter across rounds
        self.bolt_counter = 0
        # Per-round proc counter
        self.procs_this_round = 0

    def on_round_start(self, state: BattleState) -> None:
        # Reset how many times we can proc this round.
        # DO NOT reset bolt_counter (overflow carries across rounds).
        self.procs_this_round = 0

    # 🔑 New hook: called explicitly when a bolt occurs
    def on_after_bolt(self, state: BattleState, ctx: HitContext) -> None:
        # Safety: only count actual bolts
        if "bolt" not in ctx.tags or "lightning" not in ctx.tags:
            return

        # Increment persistent bolt counter
        self.bolt_counter += 1

        # Consume bolts into Tome procs, respecting per-round cap
        while (
            self.bolt_counter >= self.bolts_per_proc
            and self.procs_this_round < self.max_procs_per_round
        ):
            self.bolt_counter -= self.bolts_per_proc
            self.procs_this_round += 1

            # Fire Arcane Tome hit:
            # - skill + lightning, but NOT a "bolt"
            atk_mult_buff = 1.0 + 0.10 * state.combo_stacks

            tome_ctx = HitContext(
                damage_type=DamageType.OTHER_SKILL,
                coeff=self.coeff,  # 500% or 750%
                atk_mult_adventurer=self.adv_atk_mult,
                atk_mult_buff=atk_mult_buff,
                global_bonus=state.breath_global_this,
                tags={"skill", "lightning", "artifact"},
            )
            if state.lightning_as_ninjutsu:
                tome_ctx.tags.add("ninjutsu")
            if state.lightning_as_demonic:
                tome_ctx.tags.add("demonic")
            dmg = compute_hit_damage(tome_ctx, state)
            state.dmg_artifact += dmg

    # Optional: make on_after_hit a no-op to avoid confusion
    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        pass
