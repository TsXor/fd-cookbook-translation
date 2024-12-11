from pathlib import Path
from enum import Enum
from decimal import Decimal
import json, csv
from thefuzz import fuzz


HERE = Path(__file__).parent

DURATION_VAR = {
    'BRIEF_DURATION': 600,
    'SHORT_DURATION': 1200,
    'MEDIUM_DURATION': 3600,
    'LONG_DURATION': 6000,
}


class Effect:
    name: str
    time: int
    possibility: Decimal
    
    def __init__(self, name: str, time: str, possibility: str):
        self.name = name
        self.time = DURATION_VAR[time] if time in DURATION_VAR else int(time)
        self.possibility = Decimal(possibility)
    
    def my_repr(self):
        possibility_percentage = int(self.possibility * 100)
        ptext = '必定' if possibility_percentage == 100 else f'{possibility_percentage}%的几率'
        return f'{ptext}带来{self.time_repr()}的{self.name}效果'
    
    def time_repr(self):
        time_seconds = Decimal(self.time) / 20
        time_minutes = time_seconds // 60
        time_left_seconds = time_seconds % 60
        r = ''
        if time_minutes != Decimal(0):
            r += f'{time_minutes}分'
        if time_left_seconds != Decimal(0):
            r += f'{time_left_seconds}秒'
        if r.endswith('分'): r += '钟'
        return r


class FoodNutSatState(Enum):
    STABLE = 0
    MODIFIED = 1
    NEW = 2


class FoodCategory:
    jname: str
    nut_sat_state: FoodNutSatState
    nut_sat: tuple[Decimal, Decimal] | None = None
    nut_sat_new: tuple[Decimal, Decimal] | None = None
    effect: Effect | None = None

    def __init__(self, row: list[str]):
        jname, rnut1, rsat1, nut1, sat1, rnut2, rsat2, nut2, sat2, special_fields, \
        effect_jname, effect_name, effect_time, effect_possibility, jname = row
        
        self.jname = jname
        
        if rnut1 and rsat1:
            if not rnut2 and not rsat2:
                self.nut_sat_state = FoodNutSatState.STABLE
                self.nut_sat = (Decimal(nut1), Decimal(sat1))
            else:
                self.nut_sat_state = FoodNutSatState.MODIFIED
                if not nut2: nut2 = nut1
                if not sat2: sat2 = sat1
                self.nut_sat = (Decimal(nut1), Decimal(sat1))
                self.nut_sat_new = (Decimal(nut2), Decimal(sat2))
        else:
            self.nut_sat_state = FoodNutSatState.NEW
            self.nut_sat_new = (Decimal(nut2), Decimal(sat2))
        
        if effect_jname:
            self.effect = Effect(effect_name, effect_time, effect_possibility)
    
    def nut_sat_repr(self):
        if self.nut_sat_state == FoodNutSatState.STABLE:
            assert self.nut_sat is not None
            nut, sat = self.nut_sat
            return f'饥饿值： x{nut}， 饱和度： x{sat}'
        elif self.nut_sat_state == FoodNutSatState.MODIFIED:
            assert self.nut_sat is not None and self.nut_sat_new is not None
            nut, sat = self.nut_sat; nut_new, sat_new = self.nut_sat_new
            return f'饥饿值： $(t:<1.18.2)x{nut}$(), $(t:>=1.18.2)x{nut_new}$()， 饱和度： $(t:<1.18.2)x{sat}$(), $(t:>=1.18.2)x{sat_new}$()'
        elif self.nut_sat_state == FoodNutSatState.NEW:
            assert self.nut_sat_new is not None
            nut_new, sat_new = self.nut_sat_new
            return f'饥饿值： x{nut_new}， 饱和度： x{sat_new}'
        raise


class Food:
    category_jname: str
    name_key: str

    def __init__(self, row: list[str]):
        name_key, name_zh, category_jname = row
        self.category_jname = category_jname
        self.name_key = name_key
    
    @property
    def locale_key(self): return 'item.farmersdelight.' + self.name_key


with open(HERE / 'food_categories.csv', 'rt', encoding='utf-8-sig') as f:
    food_categories: dict[str, FoodCategory] = {}
    for i, row in enumerate(csv.reader(f)):
        if i == 0: continue
        fc = FoodCategory(row)
        food_categories[fc.jname] = fc

with open(HERE / 'food_list.csv', 'rt', encoding='utf-8-sig') as f:
    foods = [Food(row) for i, row in enumerate(csv.reader(f)) if i != 0]

with open(HERE / 'zh_cn.json', 'rt', encoding='utf-8') as f:
    zh_locale: dict[str, str] = json.load(f)

with open(HERE / 'en_us.json', 'rt', encoding='utf-8') as f:
    en_locale: dict[str, str] = json.load(f)

MATCH_RATIO_THRESH = 90

while True:
    try:
        query = input('输入食品英文名： ')
        matches = [
            (food, match_ratio) for food in foods
            if (match_ratio := fuzz.token_set_ratio(query.lower(), en_locale[food.locale_key].lower())) >= MATCH_RATIO_THRESH
        ]
        matches.sort(key=lambda info: info[1], reverse=True)
        for food, _ in matches:
            fc = food_categories[food.category_jname]
            print(f'{zh_locale[food.locale_key]}/{en_locale[food.locale_key]}： ')
            print(f'\t{fc.nut_sat_repr()}')
            if fc.effect: print(f'\t{fc.effect.my_repr()}')
        print('就这些...\n')
    except KeyboardInterrupt:
        print('say goodbye ~')
        break
