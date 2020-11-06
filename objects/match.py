# -*- coding: utf-8 -*-

from typing import Optional, Sequence, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import IntEnum, unique
from objects import glob
from objects.channel import Channel
from objects.beatmap import Beatmap
from constants.mods import Mods
from constants.gamemodes import GameMode
import packets

if TYPE_CHECKING:
    from objects.player import Player

__all__ = (
    'SlotStatus',
    'Teams',
    'MatchTypes',
    'MatchScoringTypes',
    'MatchTeamTypes',
    'ScoreFrame',
    'Slot',
    'Match'
)

@unique
class SlotStatus(IntEnum):
    open       = 1
    locked     = 2
    not_ready  = 4
    ready      = 8
    no_map     = 16
    playing    = 32
    complete   = 64
    quit       = 128

    has_player = not_ready | ready | no_map | playing | complete

@unique
class Teams(IntEnum):
    neutral = 0
    blue    = 1
    red     = 2

@unique
class MatchTypes(IntEnum):
    standard  = 0
    powerplay = 1 # literally no idea what this is for

@unique
class MatchScoringTypes(IntEnum):
    score    = 0
    accuracy = 1
    combo    = 2
    scorev2  = 3

@unique
class MatchTeamTypes(IntEnum):
    head_to_head = 0
    tag_coop     = 1
    team_vs      = 2
    tag_team_vs  = 3

@dataclass
class ScoreFrame:
    time: int
    id: int
    num300: int
    num100: int
    num50: int
    num_geki: int
    num_katu: int
    num_miss: int
    total_score: int
    current_combo: int
    max_combo: int
    perfect: bool
    current_hp: int
    tag_byte: int

    score_v2: bool
    # scorev2 only
    combo_portion: Optional[float] = None
    bonus_portion: Optional[float] = None

class Slot:
    """\
    A class to represent a single slot in an osu! multiplayer match.

    Attributes
    -----------
    player: Optional[`Player`]
        A player obj representing the player in the slot, if available.

    status: `SlotStatus`
        An obj representing the slot's current status.

    team: `Teams`
        An obj representing the slot's current team.

    mods: `int`
        The slot's currently selected mods.

    loaded: `bool`
        Whether the player is loaded into the current map.

    skipped: `bool`
        Whether the player has decided to skip the current map intro.
    """
    __slots__ = ('player', 'status', 'team',
                 'mods', 'loaded', 'skipped')

    def __init__(self) -> None:
        self.player: Optional['Player'] = None
        self.status = SlotStatus.open
        self.team = Teams.neutral
        self.mods = Mods.NOMOD
        self.loaded = False
        self.skipped = False

    def empty(self) -> bool:
        return self.player is None

    def copy(self, s) -> None:
        self.player = s.player
        self.status = s.status
        self.team = s.team
        self.mods = s.mods

    def reset(self) -> None:
        self.player = None
        self.status = SlotStatus.open
        self.team = Teams.neutral
        self.mods = Mods.NOMOD
        self.loaded = False
        self.skipped = False

class Match:
    """\
    A class to represent an osu! multiplayer match.

    Attributes
    -----------
    id: `int`
        The match's unique ID.

    name: `str`
        The match's name.

    passwd: `str`
        The match's password.

    host: `Player`
        A player obj of the match's host.

    _refs: set[`Player`]
        A set of players who have access to mp commands in the match.

    bmap: Optional[`Beatmap`]
        A beatmap obj representing the osu map.

    mods: `int`
        The match's currently selected mods.

    freemods: `bool`
        Whether the match is in freemods mode.

    mode: `int`
        The match's currently selected gamemode.

    chat: `Channel`
        A channel obj of the match's chat.

    slots: list[`Slot`]
        A list of 16 slots representing the match's slots.

    type: `MatchTypes`
        The match's currently selected match type.

    team_type: `MatchTeamTypes`
        The match's currently selected team type.

    match_scoring: `MatchScoringTypes`
        The match's currently selected match scoring type.

    in_progress: `bool`
        Whether the match is currently in progress.

    seed: `int`
        The match's randomly generated seed.
        XXX: this is used for osu!mania's random mod!
    """
    __slots__ = (
        'id', 'name', 'passwd',
        'host', '_refs', 'bmap',
        'mods', 'freemods', 'mode',
        'chat', 'slots',
        'type', 'team_type', 'match_scoring',
        'in_progress', 'seed'
    )

    def __init__(self) -> None:
        self.id = 0
        self.name = ''
        self.passwd = '' # TODO: filter from lobby

        self.host = None
        self._refs = set()

        self.bmap: Optional[Beatmap] = None

        self.mods = Mods.NOMOD
        self.mode = GameMode.vn_std
        self.freemods = False

        self.chat: Optional[Channel] = None
        self.slots = [Slot() for _ in range(16)]

        self.type = MatchTypes.standard
        self.team_type = MatchTeamTypes.head_to_head
        self.match_scoring = MatchScoringTypes.score

        self.in_progress = False
        self.seed = 0

    @property
    def url(self) -> str:
        """The match's invitation url."""
        return f'osump://{self.id}/{self.passwd}'

    @property
    def embed(self) -> str:
        """An osu! chat embed for the match."""
        return f'[{self.url} {self.name}]'

    @property
    def refs(self) -> set['Player']:
        """Return all players with referee permissions."""
        return {self.host} | self._refs

    def __contains__(self, p: 'Player') -> bool:
        return p in {s.player for s in self.slots}

    def __getitem__(self, key: Union[int, slice]) -> Slot:
        return self.slots[key]

    def __repr__(self) -> str:
        return f'<{self.name} ({self.id})>'

    def get_slot(self, p: 'Player') -> Optional[Slot]:
        # get the slot containing a given player.
        for s in self.slots:
            if p == s.player:
                return s

    def get_slot_id(self, p: 'Player') -> Optional[int]:
        # get the slot index containing a given player.
        for idx, s in enumerate(self.slots):
            if p == s.player:
                return idx

    def get_free(self) -> Optional[Slot]:
        # get the first free slot index.
        for idx, s in enumerate(self.slots):
            if s.status == SlotStatus.open:
                return idx

    def get_host_slot(self) -> Optional[Slot]:
        for s in self.slots:
            if s.status & SlotStatus.has_player \
            and s.player.id == self.host.id:
                return s

        return

    def copy(self, m: 'Match') -> None:
        """Fully copy the data of another match obj."""

        self.bmap = m.bmap
        self.freemods = m.freemods
        self.mode = m.mode
        self.team_type = m.team_type
        self.match_scoring = m.match_scoring
        self.mods = m.mods
        self.name = m.name

    def enqueue(self, data: bytes, lobby: bool = True,
                immune: Sequence[int] = []) -> None:
        """Add data to be sent to all clients in the match."""
        if not self.chat:
            breakpoint()

        self.chat.enqueue(data, immune)

        if lobby and (lchan := glob.channels['#lobby']) and lchan.players:
            lchan.enqueue(data)

    def enqueue_state(self, lobby: bool = True) -> None:
        """Enqueue `self`'s state to players in the match & lobby."""
        if not self.chat:
            breakpoint()

        # TODO: hmm this is pretty bad, writes twice

        # send password only to users currently in the match.
        self.chat.enqueue(packets.updateMatch(self, send_pw=True))

        if lobby and (lchan := glob.channels['#lobby']) and lchan.players:
            lchan.enqueue(packets.updateMatch(self, send_pw=False))

    def unready_players(self, expected: SlotStatus = SlotStatus.ready) -> None:
        """Unready any players in the `expected` state."""
        for s in self.slots:
            if s.status == expected:
                s.status = SlotStatus.not_ready

    def start(self) -> None:
        no_map: list[Player] = []

        for s in self.slots:
            # start each player who has the map.
            if s.status & SlotStatus.has_player:
                if s.status != SlotStatus.no_map:
                    s.status = SlotStatus.playing
                else:
                    no_map.append(s.player.id)

        self.in_progress = True
        self.enqueue(packets.matchStart(self), immune=no_map)
        self.enqueue_state()
