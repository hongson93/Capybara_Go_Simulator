from model.core import SimulationConfig

def get_config():
    return SimulationConfig(
        adventurer="DG",
        star=8,
        weapon="Nashir",
        combo_mastery=False,

        use_extra_end_bolts=True,
        extra_end_bolts_count=3,
        basic_atk_bolt_level=0,
        five_bolts_from_round6=False,

        rounds=15,
        basic_hits_per_round=5,
        seed=12345,

        # Your requested defaults:
        base_global_skill_bonus=0.16,      # +16% global skill damage
        base_global_lightning_bonus=0.30,   # +30% global lightning damage
        base_final_bonus=0.26,             # +26% final damage (all hits)
        base_final_skill_bonus=0.15,       # +15% final skill damage
        base_final_lightning_bonus=0.25,   # +25% final lightning damage
    )
