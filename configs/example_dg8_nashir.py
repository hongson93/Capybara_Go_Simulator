from model.core import SimulationConfig

def get_config():
    return SimulationConfig(
        adventurer="DG",
        star=8,
        weapon="Nashir",
        combo_mastery=False,

        # No extra lightning skills for now
        use_extra_end_bolts=False,
        basic_atk_bolt_level=0,
        five_bolts_from_round6=False,

        rounds=15,
        basic_hits_per_round=5,
        seed=12345,

        # New global modifiers
        base_global_bonus=0,      
        base_inbattle_bonus=0,    
        base_final_bonus=0,       
    )
