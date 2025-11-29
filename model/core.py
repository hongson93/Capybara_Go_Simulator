from dataclasses import dataclass
from typing import List, Protocol
import random

ATK_BASE = 1000.0
K_BASIC = 12.0
K_SKILL = 50.0


class DamageType:
    BASIC = "basic"
    DRAGON_FLAME = "dragon_flame"
    DRAGON_BREATH = "dragon_breath"
    OTHER_SKILL = "other_skill"

@dataclass
class BattleState:
    round_index: int = 1

    # DG-related state
    dragon_stacks: int = 0
    breath_global_next: float = 0.0
    breath_dragon_next: float = 0.0
    breath_global_this: float = 0.0
    breath_dragon_this: float = 0.0

    # Combo mastery
    combo_stacks: int = 0

    # Base multipliers (from config)
    base_global_bonus: float = 0.0          # generic global dmg
    base_inbattle_bonus: float = 0.0        # generic in-battle dmg
    base_final_bonus: float = 0.0           # generic final dmg

    # NEW: type-specific base multipliers
    base_global_lightning_bonus: float = 0.0 # +X% global dmg to lightning hits
    base_global_skill_bonus: float = 0.0    # +X% global dmg to skill hits
    base_final_skill_bonus: float = 0.0     # +X% final dmg to skill hits
    base_final_lightning_bonus: float = 0.0 # +X% final dmg to lightning hits

    # Damage accumulators
    dmg_basic: float = 0.0
    dmg_flame: float = 0.0
    dmg_breath: float = 0.0
    dmg_other: float = 0.0
    dmg_bolt: float = 0.0

    rng: random.Random | None = None




from dataclasses import dataclass, field
from typing import Set

from dataclasses import dataclass, field
from typing import Set

@dataclass
class HitContext:
    damage_type: str
    coeff: float
    is_basic: bool = False
    is_combo: bool = False
    hit_index_in_round: int = 1

    atk_base: float = ATK_BASE
    atk_mult_adventurer: float = 1.0
    atk_mult_buff: float = 1.0

    # Bracketed additive bonuses (per-hit)
    global_bonus: float = 0.0
    inbattle_bonus: float = 0.0
    final_bonus: float = 0.0

    # Tags to describe hit type, e.g. {"basic"}, {"skill", "lightning"}
    tags: Set[str] = field(default_factory=set)

    damage_done: float = 0.0



class Effect(Protocol):
    def on_round_start(self, state: BattleState) -> None: ...
    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None: ...
    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None: ...
    def on_round_end(self, state: BattleState) -> None: ...


class BaseEffect:
    def on_round_start(self, state: BattleState) -> None: ...
    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None: ...
    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None: ...
    def on_round_end(self, state: BattleState) -> None: ...


def compute_hit_damage(ctx: HitContext, state: BattleState) -> float:
    if ctx.damage_type == DamageType.BASIC:
        K = K_BASIC
    else:
        K = K_SKILL

    atk_eff = ctx.atk_base * ctx.atk_mult_adventurer * ctx.atk_mult_buff

    # --- Global bracket ---
    global_total = ctx.global_bonus + state.base_global_bonus
    if "skill" in ctx.tags:
        global_total += state.base_global_skill_bonus
    if "lightning" in ctx.tags:
        global_total += state.base_global_lightning_bonus

    # --- In-battle bracket ---
    inbattle_total = ctx.inbattle_bonus + state.base_inbattle_bonus
    # (later you can add type-specific in-battle here if you want)

    # --- Final bracket ---
    final_total = ctx.final_bonus + state.base_final_bonus
    if "skill" in ctx.tags:
        final_total += state.base_final_skill_bonus
    if "lightning" in ctx.tags:
        final_total += state.base_final_lightning_bonus

    return (
        atk_eff
        * ctx.coeff
        * K
        * (1.0 + global_total)
        * (1.0 + inbattle_total)
        * (1.0 + final_total)
    )



def simulate_adventurer(
    adv_atk_mult: float,
    effects: List[Effect],
    rounds: int = 15,
    basic_hits_per_round: int = 5,
    seed: int | None = None,
    base_global_bonus: float = 0.0,
    base_inbattle_bonus: float = 0.0,
    base_final_bonus: float = 0.0,
    base_global_skill_bonus: float = 0.0,
    base_global_lightning_bonus: float = 0.0,
    base_final_skill_bonus: float = 0.0,
    base_final_lightning_bonus: float = 0.0,
) -> BattleState:
    state = BattleState()
    state.rng = random.Random(seed) if seed is not None else random.Random()

    # Base multipliers from config
    state.base_global_bonus = base_global_bonus
    state.base_inbattle_bonus = base_inbattle_bonus
    state.base_final_bonus = base_final_bonus
    state.base_global_skill_bonus = base_global_skill_bonus
    state.base_global_lightning_bonus = base_global_lightning_bonus
    state.base_final_skill_bonus = base_final_skill_bonus
    state.base_final_lightning_bonus = base_final_lightning_bonus

    for r in range(1, rounds + 1):
        state.round_index = r

        for e in effects:
            e.on_round_start(state)

        for h in range(1, basic_hits_per_round + 1):
            ctx = HitContext(
                damage_type=DamageType.BASIC,
                coeff=1.0,
                is_basic=(h == 1),
                is_combo=(h >= 2),
                hit_index_in_round=h,
                atk_mult_adventurer=adv_atk_mult,
                tags={"basic"},
            )

            for e in effects:
                e.on_before_hit(state, ctx)

            dmg = compute_hit_damage(ctx, state)
            ctx.damage_done = dmg
            state.dmg_basic += dmg

            for e in effects:
                e.on_after_hit(state, ctx)

        # end-of-round phases
        for e in effects:
            if hasattr(e, "on_end_round_adventurer"):
                e.on_end_round_adventurer(state)
        for e in effects:
            if hasattr(e, "on_end_round_skills"):
                e.on_end_round_skills(state)
        for e in effects:
            if hasattr(e, "on_end_round_buffs_expire"):
                e.on_end_round_buffs_expire(state)
        for e in effects:
            if hasattr(e, "on_end_round_charge_release"):
                e.on_end_round_charge_release(state)

    return state


def simulate_adventurer_with_log(
    adv_atk_mult: float,
    effects: List[Effect],
    rounds: int = 15,
    basic_hits_per_round: int = 5,
    seed: int | None = None,
    base_global_bonus: float = 0.0,
    base_inbattle_bonus: float = 0.0,
    base_final_bonus: float = 0.0,
    base_global_skill_bonus: float = 0.0,
    base_global_lightning_bonus: float = 0.0,
    base_final_skill_bonus: float = 0.0,
    base_final_lightning_bonus: float = 0.0,
):
    state = BattleState()
    state.rng = random.Random(seed) if seed is not None else random.Random()

    state.base_global_bonus = base_global_bonus
    state.base_inbattle_bonus = base_inbattle_bonus
    state.base_final_bonus = base_final_bonus
    state.base_global_skill_bonus = base_global_skill_bonus
    state.base_global_lightning_bonus = base_global_lightning_bonus
    state.base_final_skill_bonus = base_final_skill_bonus
    state.base_final_lightning_bonus = base_final_lightning_bonus

    round_log = []

    for r in range(1, rounds + 1):
        state.round_index = r

        b0 = state.dmg_basic
        f0 = state.dmg_flame
        br0 = state.dmg_breath
        bolt0 = state.dmg_bolt
        other0 = state.dmg_other

        for e in effects:
            e.on_round_start(state)

        for h in range(1, basic_hits_per_round + 1):
            ctx = HitContext(
                damage_type=DamageType.BASIC,
                coeff=1.0,
                is_basic=(h == 1),
                is_combo=(h >= 2),
                hit_index_in_round=h,
                atk_mult_adventurer=adv_atk_mult,
            )

            for e in effects:
                e.on_before_hit(state, ctx)

            dmg = compute_hit_damage(ctx, state)
            ctx.damage_done = dmg
            state.dmg_basic += dmg

            for e in effects:
                e.on_after_hit(state, ctx)

        for e in effects:
            if hasattr(e, "on_end_round_adventurer"):
                e.on_end_round_adventurer(state)
        for e in effects:
            if hasattr(e, "on_end_round_skills"):
                e.on_end_round_skills(state)
        for e in effects:
            if hasattr(e, "on_end_round_buffs_expire"):
                e.on_end_round_buffs_expire(state)
        for e in effects:
            if hasattr(e, "on_end_round_charge_release"):
                e.on_end_round_charge_release(state)

        round_log.append({
            "round": r,
            "basic":  state.dmg_basic  - b0,
            "flame":  state.dmg_flame  - f0,
            "breath": state.dmg_breath - br0,
            "bolt":   state.dmg_bolt   - bolt0,
            "other":  state.dmg_other  - other0,
        })

    return state, round_log

from dataclasses import dataclass
from model.adventurers.dragon_girl import dg_effects_for_star
from model.weapons.nashir import NashirScepterEffect
from model.skills.lightning import (
    ExtraEndOfRoundBoltsEffect,
    BasicAttackBoltEffect,
    FiveBoltsAfterRound6Effect,
)
from model.skills.combo_mastery import ComboMasteryEffect  # if you want direct usage

@dataclass
class SimulationConfig:
    adventurer: str = "DG"
    star: int = 0
    weapon: str | None = None
    combo_mastery: bool = False

    use_extra_end_bolts: bool = False
    extra_end_bolts_count: int = 3
    basic_atk_bolt_level: int = 0
    five_bolts_from_round6: bool = False

    rounds: int = 15
    basic_hits_per_round: int = 5
    seed: int | None = None

    # Base generic multipliers
    base_global_bonus: float = 0.0
    base_inbattle_bonus: float = 0.0
    base_final_bonus: float = 0.0

    # NEW: type-specific multipliers
    base_global_skill_bonus: float = 0.0      # +X% global dmg to skills
    base_global_lightning_bonus: float = 0.0   # +X% global dmg to lightning hits
    base_final_skill_bonus: float = 0.0       # +X% final dmg to skills
    base_final_lightning_bonus: float = 0.0   # +X% final dmg to lightning


def build_effects_from_config(config: SimulationConfig):
    effects: List[Effect] = []

    # Adventurer core
    if config.adventurer == "DG":
        effects.extend(dg_effects_for_star(config.star, config.combo_mastery))
        adv_atk_mult = 1.15
    elif config.adventurer == "Leo":
        # TODO: plug Leo in here later
        adv_atk_mult = 1.10
    elif config.adventurer == "Daji":
        adv_atk_mult = 1.15
    else:
        adv_atk_mult = 1.0

    # Weapon
    nashir = None
    if config.weapon == "Nashir":
        nashir = NashirScepterEffect(adv_atk_mult=adv_atk_mult)
        effects.append(nashir)

    # Lightning skills
    if config.use_extra_end_bolts and config.extra_end_bolts_count > 0:
        effects.append(ExtraEndOfRoundBoltsEffect(
            adv_atk_mult=adv_atk_mult,
            n_bolts=config.extra_end_bolts_count,
            nashir=nashir,
        ))

    if config.basic_atk_bolt_level > 0:
        chance = 0.45 if config.basic_atk_bolt_level == 1 else 0.80
        effects.append(BasicAttackBoltEffect(
            adv_atk_mult=adv_atk_mult,
            chance=chance,
            nashir=nashir,
        ))

    if config.five_bolts_from_round6:
        effects.append(FiveBoltsAfterRound6Effect(
            adv_atk_mult=adv_atk_mult,
            nashir=nashir,
        ))

    return effects, adv_atk_mult


def run_simulation(config: SimulationConfig, with_log: bool = False):
    effects, adv_atk_mult = build_effects_from_config(config)

    common_kwargs = dict(
        adv_atk_mult=adv_atk_mult,
        effects=effects,
        rounds=config.rounds,
        basic_hits_per_round=config.basic_hits_per_round,
        seed=config.seed,
        base_global_bonus=config.base_global_bonus,
        base_inbattle_bonus=config.base_inbattle_bonus,
        base_final_bonus=config.base_final_bonus,
        base_global_skill_bonus=config.base_global_skill_bonus,
        base_global_lightning_bonus=config.base_global_lightning_bonus,
        base_final_skill_bonus=config.base_final_skill_bonus,
        base_final_lightning_bonus=config.base_final_lightning_bonus,
    )

    if with_log:
        return simulate_adventurer_with_log(**common_kwargs)
    else:
        return simulate_adventurer(**common_kwargs)


