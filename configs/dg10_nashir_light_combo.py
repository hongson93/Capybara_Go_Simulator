from model.core import SimulationConfig

def get_config():
    return SimulationConfig(
        debug=False,            # set True if you want per-hit debug later

        adventurer="DG",
        star=10,
        weapon="Nashir",
        combo_mastery=False,    # explicitly OFF

        # --- Lightning skills ---
        # Default: 3 extra end-of-round bolts
        use_extra_end_bolts=True,
        extra_end_bolts_count=3,

        # Basic attack bolt: level 1 = 45% chance (no upgrade version)
        #   0 = off
        #   1 = 45% proc
        #   2 = 80% proc (upgrade)
        basic_atk_bolt_level=1,

        # Five bolts from round 6: OFF for now
        five_bolts_from_round6=False,

        # Multiple Lightning: each normal bolt activates twice (no upgrade)
        #   1 = no multiplication
        #   2 = x2 (base skill)
        #   3 = x3 (upgrade)
        multiple_lightning_factor=2,

        # Lightning Charge: +6% in-battle lightning dmg per bolt, capped at 99 stacks,
        # resets every 3 rounds (logic is in core.py, here we just set the step).
        lightning_charge_step=0.06,   # 0.10 for upgrade version

        # NEW: Ezra Ring ON
        use_ezra_ring=True,
        ezra_final_light_bonus=0.20,  # +20% final lightning per round

        # --- Artifact: Arcane Tome ---
        artifact="ArcaneTome",   # enable Tome
        artifact_level=1,        # 1 = base (4 bolts, 500%), 2 = upgrade (3 bolts, 750%)


        # --- Battle settings ---
        rounds=15,
        basic_hits_per_round=5,
        seed=12345,

        # --- Base multipliers (same defaults you used earlier; tweak as you like) ---
        base_global_bonus=0,
        base_inbattle_bonus=0,
        base_final_bonus=0.26,

        base_global_skill_bonus=0.16,
        base_global_lightning_bonus=0.30,

        base_final_skill_bonus=0.15,
        base_final_lightning_bonus=0.25,

        base_inbattle_basic_bonus=0.0,
        base_inbattle_skill_bonus=0.0,
        base_inbattle_lightning_bonus=0.0,
    )
