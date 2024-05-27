class Prediction:
    def __init__(self, winning_team: str, losing_team: str, winning_pitcher: str, losing_pitcher: str, gameDate: str,
                 odds: int, confidence: str, data_points: str = '0/0'):
        self.winning_team = winning_team
        self.losing_team = losing_team
        self.winning_pitcher = winning_pitcher
        self.losing_pitcher = losing_pitcher
        self.gameDate = gameDate
        self.odds = odds
        self.confidence = confidence
        self.data_points = data_points

    def print_string(self):
        print(self.to_string())

    def to_string(self):
        if self.odds > 0:
            self.odds = f"+{self.odds}"
        elif self.odds == 0:
            self.odds = "----"
        return f"```{self.odds} {self.winning_team.upper()} over {self.losing_team.upper()} c:{self.confidence} dp:{self.data_points}```"

    def to_csv(self):
        print(f"{self.odds},{self.winning_team},{self.losing_team},{self.gameDate},{self.winning_pitcher}")

    def get_csv(self):
        return f",{self.odds},{self.winning_team},{self.losing_team},{self.gameDate},{self.winning_pitcher}"


class PitchingMatchup:
    def __init__(self, whip_advantage: int, win_percentage_advantage: int):
        self.whip_advantage = whip_advantage
        self.win_percentage_advantage = win_percentage_advantage


class Team:
    def __init__(self, abbreviation: str, id: int, name: str):
        self.abbreviation = abbreviation
        self.name = name
        self.id = id


class AdvantageScore:
    def __init__(self, home: int = 0, away: int = 0):
        self.home = home
        self.away = away


class WEIGHT:
    def __init__(self, weight: int, lower_is_better: bool):
        self.weight = weight
        self.lower_is_better = lower_is_better