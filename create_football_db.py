import sqlite3

DATABASE_FILE = "football.db"


def create_database():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob DATE,
            position TEXT,
            value REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competition_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER,
            stage_name TEXT NOT NULL UNIQUE,
            FOREIGN KEY (competition_id) REFERENCES competitions(id)
        )
    """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date DATE NOT NULL,
                season_id INTEGER,
                matchday INTEGER,
                match_status TEXT,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_score INTEGER,
                away_score INTEGER,
                competition_id INTEGER,
                stage_id INTEGER,
                referee_id INTEGER,
                FOREIGN KEY (home_team_id) REFERENCES teams(id),
                FOREIGN KEY (away_team_id) REFERENCES teams(id),
                FOREIGN KEY (competition_id) REFERENCES competitions(id),
                FOREIGN KEY (stage_id) REFERENCES competition_stages(id),
                FOREIGN KEY (referee_id) REFERENCES referees(id)
                
            )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            position TEXT,
            starter BOOLEAN,
            substitutions BOOLEAN,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            second_player_id INTEGER,
            minute INTEGER,
            added_time INTEGER,
            period TEXT,
            event_type TEXT,
            event_detail TEXT,
            home_score INTEGER,
            away_score INTEGER,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (second_player_id) REFERENCES players(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            match_id INTEGER,
            player_id INTEGER,
            team_id INTEGER,
            stat_name TEXT,
            stat_value REAL,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_stats (
            match_id INTEGER,
            team_id INTEGER,
            stat_name TEXT NOT NULL,
            stat_value REAL,
            period TEXT NOT NULL,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            team_id INTEGER,
            competition_id INTEGER,
            season_id INTEGER,
            position INTEGER,
            points INTEGER,
            played INTEGER,
            won INTEGER,
            drawn INTEGER,
            lost INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            goal_difference INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (season_id) REFERENCES seasons(id)
        )
    """)


    cursor.execute("""
            CREATE TABLE IF NOT EXISTS h2h_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date DATE,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_score INTEGER,
                away_score INTEGER,
                competition_id INTEGER,
                season_id INTEGER,
                FOREIGN KEY (home_team_id) REFERENCES teams(id),
                FOREIGN KEY (away_team_id) REFERENCES teams(id),
                FOREIGN KEY (competition_id) REFERENCES competitions(id),
                FOREIGN KEY (season_id) REFERENCES seasons(id)
            )
        """)

    connection.commit()
    connection.close()

    print("Football database created successfully.")


if __name__ == "__main__":
    create_database()
