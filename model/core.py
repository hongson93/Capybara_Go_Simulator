from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol, Set, Optional
import random

# =========================
# Constants & basic types
# =========================

ATK_BASE = 1000.0
K_BASIC = 12.0
K_SKILL = 50.0


class DamageType:
    BASIC = "basic"
    DRAGON_FLAME = "dragon_flame"
    DRAGON_BREATH = "dragon_breath"
    OTHER_SKILL = "other_skill"

    # Leo-specific types
    NINJUTSU = "ninjutsu"
    HURRICANE = "hurricane"
    ULTIMATE = "ultimate"



# =========================
# Battle state & hit context
# =========================

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

    base_global_lightning_bonus: float = 0.0   # +X% global dmg to lightning hits
    base_global_skill_bonus: float = 0.0       # +X% global dmg to skill hits
    base_global_ninjutsu_bonus: float = 0.0    # +X% global dmg to ninjutsu hits

    base_final_skill_bonus: float = 0.0        # +X% final dmg to skill hits
    base_final_lightning_bonus: float = 0.0    # +X% final dmg to lightning hits

    # Type-specific in-battle multipliers
    base_inbattle_basic_bonus: float = 0.0
    base_inbattle_skill_bonus: float = 0.0
    base_inbattle_lightning_bonus: float = 0.0

    # Lightning Charge (dynamic in-battle lightning buff from bolts)
    lightning_charge_step: float = 0.0              # per-bolt increment (0.06 or 0.10)
    lightning_charge_stacks: int = 0                # number of bolts hit in current cycle
    dynamic_inbattle_lightning_bonus: float = 0.0   # accumulated bonus from bolts

    # Temporary final lightning bonus (e.g. Ezra Ring)
    temp_final_lightning_bonus: float = 0.0

    # Ninjutsu global bonus (e.g. Leo 10★)
    dynamic_global_ninjutsu_bonus: float = 0.0  # Leo 10★ sets +0.6 here

    # Leo 5★: lightning hits gain "ninjutsu" tag
    lightning_as_ninjutsu: bool = False

    # Damage accumulators
    dmg_basic: float = 0.0
    dmg_flame: float = 0.0
    dmg_breath: float = 0.0
    dmg_other: float = 0.0        # generic misc skill damage
    dmg_bolt: float = 0.0
    dmg_artifact: float = 0.0

    # Leo-specific breakdowns
    dmg_ninjutsu: float = 0.0     # 0★/2★ ninjutsu procs
    dmg_hurricane: float = 0.0    # 4★/7★ Hurricane
    dmg_ultimate: float = 0.0     # 8★/10★ charge-release

    rng: Optional[random.Random] = None

    # All active effects for this battle (filled by the simulator)
    effects: list = field(default_factory=list, repr=False)

    # Debugging
    debug: bool = False
    debug_logs: list = field(default_factory=list)


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


# =========================
# Effect protocol + base
# =========================

class Effect(Protocol):
    def on_round_start(self, state: BattleState) -> None: ...
    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None: ...
    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None: ...
    def on_round_end(self, state: BattleState) -> None: ...


class BaseEffect:
    def on_round_start(self, state: BattleState) -> None:
        pass

    def on_before_hit(self, state: BattleState, ctx: HitContext) -> None:
        pass

    def on_after_hit(self, state: BattleState, ctx: HitContext) -> None:
        pass

    def on_round_end(self, state: BattleState) -> None:
        pass


# =========================
# Debug logging helper
# =========================

def debug_log_hit(
    state: BattleState,
    ctx: HitContext,
    K: float,
    atk_eff: float,
    global_total: float,
    inbattle_total: float,
    final_total: float,
    dmg: float,
) -> None:
    if not state.debug:
        return

    state.debug_logs.append({
        "round": state.round_index,
        "hit_index": ctx.hit_index_in_round,
        "type": ctx.damage_type,
        "tags": sorted(list(ctx.tags)),
        "coeff": ctx.coeff,
        "atk_eff": atk_eff,
        "K": K,
        "global_total": global_total,
        "inbattle_total": inbattle_total,
        "final_total": final_total,
        "damage": dmg,
        "lc_stacks": state.lightning_charge_stacks,
        "lc_bonus": state.dynamic_inbattle_lightning_bonus,
    })


# =========================
# Core damage computation
# =========================

def compute_hit_damage(ctx: HitContext, state: BattleState) -> float:
    # Choose damage constant
    if ctx.damage_type == DamageType.BASIC:
        K = K_BASIC
    else:
        K = K_SKILL

    # Effective ATK
    atk_eff = ctx.atk_base * ctx.atk_mult_adventurer * ctx.atk_mult_buff

    # --- Global bracket ---
    global_total = ctx.global_bonus + state.base_global_bonus
    if "skill" in ctx.tags:
        global_total += state.base_global_skill_bonus
    if "lightning" in ctx.tags:
        global_total += state.base_global_lightning_bonus
    if "ninjutsu" in ctx.tags:
        global_total += state.base_global_ninjutsu_bonus
        global_total += state.dynamic_global_ninjutsu_bonus

    # --- In-battle bracket ---
    inbattle_total = ctx.inbattle_bonus + state.base_inbattle_bonus
    if "basic" in ctx.tags:
        inbattle_total += state.base_inbattle_basic_bonus
    if "skill" in ctx.tags:
        inbattle_total += state.base_inbattle_skill_bonus
    if "lightning" in ctx.tags:
        inbattle_total += state.base_inbattle_lightning_bonus
        inbattle_total += state.dynamic_inbattle_lightning_bonus

    # --- Final bracket ---
    final_total = ctx.final_bonus + state.base_final_bonus
    if "skill" in ctx.tags:
        final_total += state.base_final_skill_bonus
    if "lightning" in ctx.tags:
        final_total += state.base_final_lightning_bonus
        final_total += state.temp_final_lightning_bonus

    dmg = (
        atk_eff
        * ctx.coeff
        * K
        * (1.0 + global_total)
        * (1.0 + inbattle_total)
        * (1.0 + final_total)
    )

    # Debug logging
    debug_log_hit(state, ctx, K, atk_eff, global_total, inbattle_total, final_total, dmg)

    # Lightning Charge: after a bolt hit, increase stacks (up to 99) and recompute bonus
    if "bolt" in ctx.tags and "lightning" in ctx.tags and state.lightning_charge_step > 0.0:
        if state.lightning_charge_stacks < 99:
            state.lightning_charge_stacks += 1
            state.dynamic_inbattle_lightning_bonus = (
                state.lightning_charge_stacks * state.lightning_charge_step
            )

    return dmg


# =========================
# Generic simulator
# =========================

def simulate_adventurer(
    adv_atk_mult: float,
    effects: List[Effect],
    rounds: int = 15,
    basic_hits_per_round: int = 5,
    seed: Optional[int] = None,
    base_global_bonus: float = 0.0,
    base_inbattle_bonus: float = 0.0,
    base_final_bonus: float = 0.0,
    base_global_skill_bonus: float = 0.0,
    base_global_lightning_bonus: float = 0.0,
    base_global_ninjutsu_bonus: float = 0.0,
    base_final_skill_bonus: float = 0.0,
    base_final_lightning_bonus: float = 0.0,
    base_inbattle_basic_bonus: float = 0.0,
    base_inbattle_skill_bonus: float = 0.0,
    base_inbattle_lightning_bonus: float = 0.0,
    debug: bool = False,
    lightning_charge_step: float = 0.0,
) -> BattleState:
    state = BattleState()
    state.effects = effects
    state.rng = random.Random(seed) if seed is not None else random.Random()
    state.debug = debug
    state.debug_logs = []

    # Base multipliers from config
    state.base_global_bonus = base_global_bonus
    state.base_inbattle_bonus = base_inbattle_bonus
    state.base_final_bonus = base_final_bonus

    state.base_global_skill_bonus = base_global_skill_bonus
    state.base_global_lightning_bonus = base_global_lightning_bonus
    state.base_global_ninjutsu_bonus = base_global_ninjutsu_bonus

    state.base_final_skill_bonus = base_final_skill_bonus
    state.base_final_lightning_bonus = base_final_lightning_bonus

    state.base_inbattle_basic_bonus = base_inbattle_basic_bonus
    state.base_inbattle_skill_bonus = base_inbattle_skill_bonus
    state.base_inbattle_lightning_bonus = base_inbattle_lightning_bonus

    # Lightning Charge
    state.lightning_charge_step = lightning_charge_step
    state.dynamic_inbattle_lightning_bonus = 0.0
    state.lightning_charge_stacks = 0

    # Ninjutsu dynamic buff + lightning-as-ninjutsu default
    state.dynamic_global_ninjutsu_bonus = 0.0
    state.lightning_as_ninjutsu = False

    for r in range(1, rounds + 1):
        state.round_index = r

        # Round start
        for e in effects:
            e.on_round_start(state)

        # Basic attacks + combos
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

        # End-of-round phases
        # 1) Adventurer end-of-round skills (e.g. Dragon Breath)
        for e in effects:
            if hasattr(e, "on_end_round_adventurer"):
                e.on_end_round_adventurer(state)

        # 2) End-of-round skill procs (e.g. extra bolts, per-round bolts)
        for e in effects:
            if hasattr(e, "on_end_round_skills"):
                e.on_end_round_skills(state)

        # 3) Buffs with round limit expire here
        for e in effects:
            if hasattr(e, "on_end_round_buffs_expire"):
                e.on_end_round_buffs_expire(state)

        # Lightning Charge reset every 3 rounds,
        # AFTER buffs expire, BEFORE charge release
        if state.lightning_charge_step > 0.0 and (state.round_index % 3 == 0):
            state.lightning_charge_stacks = 0
            state.dynamic_inbattle_lightning_bonus = 0.0

        # 4) Charge release (e.g. Nashir's 6 thunder bolts)
        for e in effects:
            if hasattr(e, "on_end_round_charge_release"):
                e.on_end_round_charge_release(state)

    return state


def simulate_adventurer_with_log(
    adv_atk_mult: float,
    effects: List[Effect],
    rounds: int = 15,
    basic_hits_per_round: int = 5,
    seed: Optional[int] = None,
    base_global_bonus: float = 0.0,
    base_inbattle_bonus: float = 0.0,
    base_final_bonus: float = 0.0,
    base_global_skill_bonus: float = 0.0,
    base_global_lightning_bonus: float = 0.0,
    base_global_ninjutsu_bonus: float = 0.0,
    base_final_skill_bonus: float = 0.0,
    base_final_lightning_bonus: float = 0.0,
    base_inbattle_basic_bonus: float = 0.0,
    base_inbattle_skill_bonus: float = 0.0,
    base_inbattle_lightning_bonus: float = 0.0,
    debug: bool = False,
    lightning_charge_step: float = 0.0,
):
    state = BattleState()
    state.effects = effects
    state.rng = random.Random(seed) if seed is not None else random.Random()
    state.debug = debug
    state.debug_logs = []

    state.base_global_bonus = base_global_bonus
    state.base_inbattle_bonus = base_inbattle_bonus
    state.base_final_bonus = base_final_bonus

    state.base_global_skill_bonus = base_global_skill_bonus
    state.base_global_lightning_bonus = base_global_lightning_bonus
    state.base_global_ninjutsu_bonus = base_global_ninjutsu_bonus

    state.base_final_skill_bonus = base_final_skill_bonus
    state.base_final_lightning_bonus = base_final_lightning_bonus

    state.base_inbattle_basic_bonus = base_inbattle_basic_bonus
    state.base_inbattle_skill_bonus = base_inbattle_skill_bonus
    state.base_inbattle_lightning_bonus = base_inbattle_lightning_bonus

    # Lightning Charge
    state.lightning_charge_step = lightning_charge_step
    state.dynamic_inbattle_lightning_bonus = 0.0
    state.lightning_charge_stacks = 0

    # Ninjutsu dynamic buff + lightning-as-ninjutsu default
    state.dynamic_global_ninjutsu_bonus = 0.0
    state.lightning_as_ninjutsu = False

    round_log = []

    for r in range(1, rounds + 1):
        state.round_index = r

        b0 = state.dmg_basic
        f0 = state.dmg_flame
        br0 = state.dmg_breath
        bolt0 = state.dmg_bolt
        other0 = state.dmg_other

        # Round start
        for e in effects:
            e.on_round_start(state)

        # Basic attacks + combos
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

        # End-of-round phases
        # 1) Adventurer end-of-round skills (e.g. Dragon Breath)
        for e in effects:
            if hasattr(e, "on_end_round_adventurer"):
                e.on_end_round_adventurer(state)

        # 2) End-of-round skill procs (e.g. extra bolts, per-round bolts)
        for e in effects:
            if hasattr(e, "on_end_round_skills"):
                e.on_end_round_skills(state)

        # 3) Buffs with round limit expire here
        for e in effects:
            if hasattr(e, "on_end_round_buffs_expire"):
                e.on_end_round_buffs_expire(state)

        # Lightning Charge reset every 3 rounds,
        # AFTER buffs expire, BEFORE charge release
        if state.lightning_charge_step > 0.0 and (state.round_index % 3 == 0):
            state.lightning_charge_stacks = 0
            state.dynamic_inbattle_lightning_bonus = 0.0

        # 4) Charge release (e.g. Nashir's 6 thunder bolts)
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


# =========================
# Config & builder
# =========================

from model.adventurers.dragon_girl import dg_effects_for_star
from model.adventurers.leo import leo_effects_for_star
from model.weapons.nashir import NashirScepterEffect
from model.skills.lightning import (
    ExtraEndOfRoundBoltsEffect,
    BasicAttackBoltEffect,
    FiveBoltsAfterRound6Effect,
)
from model.skills.combo_mastery import ComboMasteryEffect
from model.skills.ezra_ring import EzraRingEffect
from model.artifacts.arcane_tome import ArcaneTomeEffect


@dataclass
class SimulationConfig:
    debug: bool = False
    adventurer: str = "DG"
    star: int = 0
    weapon: Optional[str] = None
    combo_mastery: bool = False

    use_extra_end_bolts: bool = True
    extra_end_bolts_count: int = 3
    basic_atk_bolt_level: int = 0  # 0 = off, 1 = base, 2 = upgraded
    five_bolts_from_round6: bool = False

    rounds: int = 15
    basic_hits_per_round: int = 5
    seed: Optional[int] = None

    # Base generic multipliers
    base_global_bonus: float = 0.0
    base_inbattle_bonus: float = 0.0
    base_final_bonus: float = 0.0

    # Type-specific global/final
    base_global_skill_bonus: float = 0.0
    base_global_lightning_bonus: float = 0.0
    base_global_ninjutsu_bonus: float = 0.0
    base_final_skill_bonus: float = 0.0
    base_final_lightning_bonus: float = 0.0

    # Type-specific in-battle
    base_inbattle_basic_bonus: float = 0.0
    base_inbattle_skill_bonus: float = 0.0
    base_inbattle_lightning_bonus: float = 0.0

    # Lightning Charge per-bolt step
    lightning_charge_step: float = 0.0  # 0.06 for base, 0.10 for upgrade
    multiple_lightning_factor: int = 1

    # Ezra Ring toggle & strength
    use_ezra_ring: bool = False
    ezra_final_light_bonus: float = 0.20  # +20% final lightning for 1 round

    # Artifact system
    artifact: Optional[str] = None      # e.g. "ArcaneTome"
    artifact_level: int = 0            # 0 = off, 1 = base, 2 = upgraded


def build_effects_from_config(config: SimulationConfig):
    effects: List[Effect] = []

    # Adventurer core
    if config.adventurer == "DG":
        effects.extend(dg_effects_for_star(config.star, config.combo_mastery))
        adv_atk_mult = 1.15
    elif config.adventurer == "Leo":
        effects.extend(leo_effects_for_star(config.star, config.combo_mastery))
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

    # Ezra Ring
    if config.use_ezra_ring:
        effects.append(EzraRingEffect(
            adv_atk_mult=adv_atk_mult,
            final_light_bonus=config.ezra_final_light_bonus,
        ))

    # Lightning skills
    if config.use_extra_end_bolts and config.extra_end_bolts_count > 0:
        effects.append(ExtraEndOfRoundBoltsEffect(
            adv_atk_mult=adv_atk_mult,
            n_bolts=config.extra_end_bolts_count,
            nashir=nashir,
            multi_factor=config.multiple_lightning_factor,
        ))

    if config.basic_atk_bolt_level > 0:
        # Base chances
        if config.basic_atk_bolt_level == 1:
            chance = 0.45
        else:  # level 2 (upgrade)
            chance = 0.75  # corrected: 75%, not 80%

        # Leo passive: improved on-hit chance
        if config.adventurer == "Leo":
            if config.basic_atk_bolt_level == 1:
                chance = 0.8336
            else:  # upgraded
                chance = 0.984

        effects.append(BasicAttackBoltEffect(
            adv_atk_mult=adv_atk_mult,
            chance=chance,
            nashir=nashir,
            multi_factor=config.multiple_lightning_factor,
        ))

    if config.five_bolts_from_round6:
        effects.append(FiveBoltsAfterRound6Effect(
            adv_atk_mult=adv_atk_mult,
            nashir=nashir,
            multi_factor=config.multiple_lightning_factor,
        ))

    # Artifact
    if config.artifact == "ArcaneTome" and config.artifact_level > 0:
        if config.artifact_level == 1:
            bolts_per_proc = 4
            coeff = 5.0   # 500%
        else:  # level 2 (upgrade)
            bolts_per_proc = 3
            coeff = 7.5   # 750%

        effects.append(
            ArcaneTomeEffect(
                adv_atk_mult=adv_atk_mult,
                bolts_per_proc=bolts_per_proc,
                coeff=coeff,
            )
        )

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
        base_global_ninjutsu_bonus=config.base_global_ninjutsu_bonus,
        base_final_skill_bonus=config.base_final_skill_bonus,
        base_final_lightning_bonus=config.base_final_lightning_bonus,
        base_inbattle_basic_bonus=config.base_inbattle_basic_bonus,
        base_inbattle_skill_bonus=config.base_inbattle_skill_bonus,
        base_inbattle_lightning_bonus=config.base_inbattle_lightning_bonus,
        debug=config.debug,
        lightning_charge_step=config.lightning_charge_step,
    )

    if with_log:
        return simulate_adventurer_with_log(**common_kwargs)
    else:
        return simulate_adventurer(**common_kwargs)
