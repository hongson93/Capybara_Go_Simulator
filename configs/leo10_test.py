from model.core import SimulationConfig, run_simulation, print_damage_breakdown

cfg_leo_tome = SimulationConfig(
    # Core identity
    debug=True,                 # enable debug_logs if you want to inspect hits
    adventurer="Leo",
    star=10,
    weapon="Nashir",
    combo_mastery=False,

    # Lightning skills
    use_extra_end_bolts=True,  # keep these off so Tome stands out clearly
    extra_end_bolts_count=3,
    basic_atk_bolt_level=1,     # upgraded basic attack bolt
    five_bolts_from_round6=False,

    # Battle length / RNG
    rounds=15,
    basic_hits_per_round=5,
    seed=42,

    # Base multipliers (set to 0 so you only see Leo + Tome effects)
    base_global_bonus=0.0,
    base_inbattle_bonus=0.0,
    base_final_bonus=0.26,            # +26% final damage (all hits)
    base_global_skill_bonus=0.56,     # +16% global skill damage
    base_global_lightning_bonus=0.30,  # +30% global lightning damage
    base_global_ninjutsu_bonus=0.0,
    base_global_combo_bonus=1.0,     # +100% global combo damage
    base_final_skill_bonus=0.15,      # +15% final skill damage
    base_final_lightning_bonus=0.25,   # +25% final lightning damage
    base_inbattle_basic_bonus=0.0,
    base_inbattle_skill_bonus=0.0,
    base_inbattle_lightning_bonus=0.0,

    # Lightning Charge
    lightning_charge_step=0,     # or 0.10 if you want upgraded LC
    multiple_lightning_factor=1,

    # Ezra Ring
    use_ezra_ring=True,            # off for this example
    ezra_final_light_bonus=0.20,

    # Artifact: Arcane Tome enabled and upgraded
    artifact="ArcaneTome",          # make sure this matches your string
    artifact_level=1,               # 1 = base, 2 = upgraded
)
