class Prediction:
    def __init__(self, winning_team: str, losing_team: str, winning_pitcher: str, losing_pitcher: str, gameDate: str,
                 odds: int):
        self.winning_team = winning_team
        self.losing_team = losing_team
        self.winning_pitcher = winning_pitcher
        self.losing_pitcher = losing_pitcher
        self.gameDate = gameDate
        self.odds = odds

    def to_string(self):
        print(
            f"{self.odds} {self.winning_team} over {self.losing_team} at home on {self.gameDate}.  WP: {self.winning_pitcher}")

    def get_string(self):
        return f"{self.odds} {self.winning_team} over {self.losing_team} at home on {self.gameDate}.  WP: {self.winning_pitcher}\n"

    def to_csv(self):
        print(f"{self.odds},{self.winning_team},{self.losing_team},{self.gameDate},{self.winning_pitcher}")

    def get_csv(self):
        return f",{self.odds},{self.winning_team},{self.losing_team},{self.gameDate},{self.winning_pitcher}"

class PitchingMatchup:
    def __init__(self, whip_advantage: int, win_percentage_advantage: int):
        self.whip_advantage = whip_advantage
        self.win_percentage_advatage = win_percentage_advantage


class Team:
    def __init__(self, abbreviation: str, id: int, name: str):
        self.abbreviation = abbreviation
        self.name = name
        self.id = id


class AdvantageScore:
    def __init__(self, home: int = 0, away: int = 0):
        self.home = home
        self.away = away