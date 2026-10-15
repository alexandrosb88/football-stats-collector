import asyncio
import pandas as pd
import re
import sqlite3
from playwright.async_api import async_playwright
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re

# CONFIG — change this to your league/championship page
CHAMPIONSHIP_URL = "https://www.soccerway.com/greece/super-league/results/"  # ← replace with actual URL
CSV_FILE = "superleague_stats.csv"



def get_or_create_team(name, city=None):

    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    # Check whether the team already exists
    cursor.execute(
        "SELECT id FROM teams WHERE name = ?",
        (name,)
    )

    result = cursor.fetchone()

    if result:
        team_id = result[0]

    else:
        # Team does not exist, so create it
        cursor.execute(
            "INSERT INTO teams (name, city) VALUES (?, ?)",
            (name, city)
        )

        team_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return team_id


def get_or_create_player(name):
    if not name:
        return None

    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM players WHERE name = ?",
        (name,)
    )

    result = cursor.fetchone()

    if result:
        player_id = result[0]
    else:
        cursor.execute(
            "INSERT INTO players (name) VALUES (?)",
            (name,)
        )
        player_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return player_id


def get_or_create_competition(name):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM competitions WHERE name = ?",
        (name,)
    )

    result = cursor.fetchone()

    if result:
        competition_id = result[0]
    else:
        cursor.execute(
            "INSERT INTO competitions (name) VALUES (?)",
            (name,)
        )
        competition_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return competition_id 


def add_competition(name):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO competitions (name) VALUES (?)",
        (name,)
    )

    conn.commit()
    conn.close()


def get_or_create_season(name):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM seasons WHERE name = ?",
        (name,)
    )

    result = cursor.fetchone()

    if result:
        season_id = result[0]
    else:
        cursor.execute(
            "INSERT INTO seasons (name) VALUES (?)",
            (name,)
        )
        season_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return season_id   


def add_season(name):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO seasons (name) VALUES (?)",
        (name,)
    )

    conn.commit()
    conn.close()

 


def add_competition_stage(competition_id, stage_name):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO competition_stages
        (competition_id, stage_name)
        VALUES (?, ?)
        """,
        (competition_id, stage_name)
    )

    conn.commit()
    conn.close()

def get_or_create_referee(name):

    if not name:
        return None

    
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM referees WHERE name = ?",
        (name,)
    )

    result = cursor.fetchone()

    if result:
        referee_id = result[0]
    else:
        cursor.execute(
            "INSERT INTO referees (name) VALUES (?)",
            (name,)
        )
        referee_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return referee_id



def save_match(match):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO matches (
            match_date,
            season_id,
            matchday,
            match_status,
            home_team_id,
            away_team_id,
            home_score,
            away_score,
            competition_id,
            stage_id,
            referee_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match["match_date"],
        match["season_id"],
        match["matchday"],
        match["match_status"],
        match["home_team_id"],
        match["away_team_id"],
        match["home_score"],
        match["away_score"],
        match["competition_id"],
        match["stage_id"],
        match["referee_id"]
    ))

    conn.commit()

    match_id = cursor.lastrowid

    conn.close()

    return match_id



def save_events(match_id, events):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    for event in events:
        cursor.execute("""
            INSERT INTO events (
                match_id,
                team_id,
                player_id,
                second_player_id,
                assist_player_id,
                minute,
                added_time,
                period,
                event_type,
                event_detail,
                home_score,
                away_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            event["team_id"],
            event["player_id"],
            event["second_player_id"],
            event["assist_player_id"],
            event["minute"],
            event["added_time"],
            event["period"],
            event["event_type"],
            event["event_detail"],
            event["home_score"],
            event["away_score"]
        ))

    conn.commit()
    conn.close()


def save_lineups(match_id, lineups):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    for lineup in lineups:
        cursor.execute("""
            INSERT INTO lineups (
                match_id,
                team_id,
                player_id,
                position,
                starter,
                substitutions,
                formation_row,
                formation_order,
                rating
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            lineup["team_id"],
            lineup["player_id"],
            lineup["position"],
            lineup["starter"],
            lineup["substitutions"],
            lineup["formation_row"],
            lineup["formation_order"],
            lineup["rating"]
        ))

    conn.commit()
    conn.close()



def save_team_stats(match_id, team_stats):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    try:
        for stat in team_stats:
            cursor.execute("""
                INSERT INTO team_stats (
                    match_id,
                    team_id,
                    stat_name,
                    stat_value,
                    period
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (
                    match_id,
                    team_id,
                    stat_name,
                    period
                )
                DO UPDATE SET
                    stat_value = excluded.stat_value
            """, (
                match_id,
                stat["team_id"],
                stat["stat_name"],
                stat["stat_value"],
                stat["period"]
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


async def get_text(element, selector: str) -> str:
    """Return the text content of a subelement or empty string if not found."""
    el = await element.query_selector(selector)
    return (await el.text_content()) if el else ""


async def get_match_links(page, championship_url):
    await page.goto(championship_url, wait_until="networkidle")

    # selector for the "show more matches" button
    button_selector = "button[data-testid='wcl-buttonLink']"

    while True:
        button = page.locator(button_selector)

        if await button.count() == 0:
            break

        try:
            # scroll into view (IMPORTANT)
            await button.scroll_into_view_if_needed()

            # click with force (bypasses overlay issues)
            await button.click(force=True)

            # wait for DOM update (better than sleep)
            await page.wait_for_timeout(1500)

        except Exception as e:
            print("Click failed:", e)
            break

    # now extract all match links
    links = await page.eval_on_selector_all(
        "div.event__match a.eventRowLink",
        "els => els.map(el => el.href)"
    )

    #print(links)

    for link in links:
        print(link)

    return list(set(links))


  

async def parse_match(
    page,
    match_url,
    competition_id,
    season_id,
    stage_id
        ):
    await page.goto(match_url, wait_until="networkidle")



    #Get Team stats links
    parsed_url = urlparse(match_url)

    mid = parse_qs(parsed_url.query).get("mid", [None])[0]

    # Build the base URL without the existing query string
    base_url = match_url.split("?")[0].rstrip("/")

    stats_urls = {
        "full_match": f"{base_url}/summary/stats/overall/" + (f"?mid={mid}" if mid else ""),
        "first_half": f"{base_url}/summary/stats/1st-half/" + (f"?mid={mid}" if mid else ""),
        "second_half": f"{base_url}/summary/stats/2nd-half/" + (f"?mid={mid}" if mid else ""),
    }

    print("Full-match stats URL:", stats_urls["full_match"])



    player_stats_urls = {
        "top": f"{base_url}/summary/player-stats/top/" + (f"?mid={mid}" if mid else ""),
        "shots": f"{base_url}/summary/player-stats/shots/" + (f"?mid={mid}" if mid else ""),
        "attack": f"{base_url}/summary/player-stats/attack/" + (f"?mid={mid}" if mid else ""),
        "passes": f"{base_url}/summary/player-stats/passes/" + (f"?mid={mid}" if mid else ""),
        "defense": f"{base_url}/summary/player-stats/defense/" + (f"?mid={mid}" if mid else ""),
        "goalkeeping": f"{base_url}/summary/player-stats/goalkeeping/" + (f"?mid={mid}" if mid else ""),
        "general": f"{base_url}/summary/player-stats/general/" + (f"?mid={mid}" if mid else ""),
    }



    #### TEST PLAYER STATS ####


    # Collect player statistics from all seven categories
    all_player_stats = []

    for category, stats_url in player_stats_urls.items():
        try:
            print(f"Navigating to {category} player statistics...")

            await page.goto(
                stats_url,
                wait_until="domcontentloaded"
            )

            await page.wait_for_selector(
                'table[data-testid="wcl-table"]',
                timeout=15000
            )

            category_stats = await parse_player_stats(page)

            print(
                f"{category}: collected "
                f"{len(category_stats)} player-stat records"
            )

            all_player_stats.extend(category_stats)

        except Exception as e:
            print(f"Could not collect {category} player statistics: {e}")

    print("Total player-stat records:", len(all_player_stats))

    #### TEST PLAYER STATS ####



    #Date
    match_datetime_text = await get_text(
    page,
    "div.duelParticipant__startTime"
    )

    print("Match Date/Time:", match_datetime_text)

    match_datetime = datetime.strptime(
        match_datetime_text,
        "%d.%m.%Y %H:%M"
    )

    match_date = match_datetime.date()

    print("Match Date:", match_date)


    #Matchday
    og_description = await page.get_attribute(
    'meta[property="og:description"]',
    "content"
    ) or ""

    print("Description:", og_description)

    round_match = re.search(r"Round\s+(\d+)", og_description)

    if round_match:
        matchday = int(round_match.group(1))
    else:
        matchday = None

    print("Matchday:", matchday)


    # Match Status
    match_status = await get_text(
        page,
        "span.fixedHeaderDuel__detailStatus"
    )

    print("Match Status:", match_status)
    

    # Teams
    home_team = (await page.get_attribute("div.duelParticipant__home img.participant__image",
    "alt")) or ""
    away_team = (await page.get_attribute("div.duelParticipant__away img.participant__image",
    "alt")) or ""

    home_team_id = get_or_create_team(home_team)
    away_team_id = get_or_create_team(away_team)

    print("Home Team:", home_team)
    print("Home Team ID:", home_team_id)

    print("Away Team:", away_team)
    print("Away Team ID:", away_team_id)

    print ("Home Team: " + home_team + " vs Away Team: " + away_team)

    # Score
    score = (await page.text_content("div.detailScore__wrapper")) or ""
    goals = score.split("-")
    home_goals = int(goals[0])
    away_goals = int(goals[1])
    print ("Score: " + score)
    print ("Home Goals: " + str(home_goals))
    print ("Away Goals: " + str(away_goals))

    # Cards
    yellow_card_counter = 0
    red_card_counter = 0
    
    # Events (goals, cards, etc.)
    events = []

    home_incidents = (await page.query_selector_all("li.smv__participantRow.smv__homeParticipant"))
    print(f"Found {len(home_incidents)} home incidents")


    for incident in home_incidents:

        time = await get_text(incident, "div.smv__timeBox")

        minute = None
        added_time = 0

        if time:
            time_clean = time.replace("'", "").strip()

            if "+" in time_clean:
                parts = time_clean.split("+")
                minute = int(parts[0])
                added_time = int(parts[1])
            else:
                minute = int(time_clean)

        print(f"Raw time: {time} → Minute: {minute}, Added time: {added_time}")

        player = await get_text(incident, "a.smv__playerName")

        player_id = None
        
        if player:
            player_id = get_or_create_player(player)

        assist_player = await get_text(
            incident,
            "div.smv__assist a"
        )

        assist_player_id = None

        if assist_player:
            assist_player_id = get_or_create_player(assist_player)


        player_out = await get_text(
            incident,
            "a.smv__subDown.smv__playerName"
        )

        second_player_id = None

        if player_out:
            second_player_id = get_or_create_player(player_out)


        svg_title = await get_text(
            incident,
            "div.smv__incidentIcon svg title"
        )

        svg_title = await get_text(
            incident,
            "div.smv__incidentIcon svg title"
        )
                
        svg = await incident.query_selector(
            "div.smv__incidentIcon svg"
        )
        
        incident_icon = None
        svg_class = None
        
        if svg:
            incident_icon = await svg.get_attribute("data-testid")
            svg_class = await svg.get_attribute("class")

        svg_title_substitution = await get_text(
            incident,
            "div.smv__incidentIconSub svg title"
        )


        if incident_icon == "wcl-icon-incidents-goal-soccer":

            if "footballOwnGoal-ico" in (svg_class or ""):
                event_detail = "own_goal"
            else:
                event_detail = "normal"

            print(f"{time} - Goal - {player} - {event_detail}")

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": second_player_id,
                "assist_player_id": assist_player_id,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "goal",
                "event_detail": event_detail,
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif "yellowCard-ico" in (svg_class or ""):

            print(f"{time} - Yellow Card - {player}")

            yellow_card_counter += 1

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "assist_player_id": None,
                "second_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "card",
                "event_detail": "yellow",
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif "redCard-ico" in (svg_class or ""):

            print(f"{time} - Red Card - {player}")

            red_card_counter += 1

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": None,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "card",
                "event_detail": "red",
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif "Substitution" in (svg_title_substitution or ""):

            print(
                f"{time} - player in {player} - player out {player_out}"
            )

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": second_player_id,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "substitution",
                "event_detail": None,
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif incident_icon == "wcl-icon-incidents-penalty-missed":

            print(f"{time} - Penalty missed - {player}")

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": None,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "penalty",
                "event_detail": "missed",
                "home_score": home_goals,
                "away_score": away_goals
            })

                
    away_incidents = await page.query_selector_all(
    "li.smv__participantRow.smv__awayParticipant"
)

    print(f"Found {len(away_incidents)} away incidents")

    for incident in away_incidents:

        time = await get_text(
            incident,
            "div.smv__timeBox"
        )

        minute = None
        added_time = 0

        if time:
            time_clean = time.replace("'", "").strip()

            if "+" in time_clean:
                parts = time_clean.split("+")
                minute = int(parts[0])
                added_time = int(parts[1])
            else:
                minute = int(time_clean)

        print(
            f"Raw time: {time} → "
            f"Minute: {minute}, Added time: {added_time}"
        )

        
        player = await get_text(incident, "a.smv__playerName")

        player_id = None

        if player:
            player_id = get_or_create_player(player)


        assist_player = await get_text(
            incident,
            "div.smv__assist a"
        )

        assist_player_id = None

        if assist_player:
            assist_player_id = get_or_create_player(assist_player)

        player_out = await get_text(
            incident,
            "a.smv__subDown.smv__playerName"
        )
        
        second_player_id = None

        if player_out:
            second_player_id = get_or_create_player(player_out)

        svg_title = await get_text(
                    incident,
                    "div.smv__incidentIcon svg title"
                )
        
        svg = await incident.query_selector(
                "div.smv__incidentIcon svg"
            )

        incident_icon = None
        svg_class = None

        if svg:
            incident_icon = await svg.get_attribute("data-testid")
            svg_class = await svg.get_attribute("class")
        
        svg_title_substitution = await get_text(
                    incident,
                    "div.smv__incidentIconSub svg title"
                )


        if incident_icon == "wcl-icon-incidents-goal-soccer":

            if "footballOwnGoal-ico" in (svg_class or ""):
                event_detail = "own_goal"
            else:
                event_detail = "normal"

            print(f"{time} - Goal - {player} - {event_detail}")

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": None,
                "assist_player_id": assist_player_id,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "goal",
                "event_detail": event_detail,
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif "yellowCard-ico" in (svg_class or ""):

            print(f"{time} - Yellow Card - {player}")

            yellow_card_counter += 1

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": None,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "card",
                "event_detail": "yellow",
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif "redCard-ico" in (svg_class or ""):

            print(f"{time} - Red Card - {player}")

            red_card_counter += 1

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": None,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "card",
                "event_detail": "red",
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif "Substitution" in (svg_title_substitution or ""):

            print(
                f"{time} - player in {player} - player out {player_out}"
            )

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": second_player_id,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "substitution",
                "event_detail": None,
                "home_score": home_goals,
                "away_score": away_goals
            })


        elif incident_icon == "wcl-icon-incidents-penalty-missed":

            print(f"{time} - Penalty missed - {player}")

            events.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "second_player_id": None,
                "assist_player_id": None,
                "minute": minute,
                "added_time": added_time,
                "period": None,
                "event_type": "penalty",
                "event_detail": "missed",
                "home_score": home_goals,
                "away_score": away_goals
            })

    # Referee
    referee = ""
    try:
        referee = (await get_text(page, "div.wcl-infoValue_grawU"))
        referee = referee.replace("\xa0", " ").strip()

        print("Referee: ", referee)


    except:
        pass

    referee_id = get_or_create_referee(referee)

    # Lineups — navigate to the lineup subpage
    base_url = match_url.split("?")[0].rstrip("/")
    mid = match_url.split("mid=")[-1] if "mid=" in match_url else ""

    lineups_url = f"{base_url}/summary/lineups/" + (
        f"?mid={mid}" if mid else ""
    )

    print(f"Navigating to lineups page: {lineups_url}")

    await page.goto(
    lineups_url,
    wait_until="domcontentloaded"
    )

    await page.wait_for_selector(
        "[data-testid='wcl-lineupsGroup']",
        timeout=10000
    )

    lineups = await parse_lineups(
        page,
        home_team_id,
        away_team_id
    )

    print(f"Total lineup players found: {len(lineups)}")

     
    
    # Team stats — full match, first half, and second half
    team_stats = []

    periods = {
        "full_time": stats_urls["full_match"],
        "first_half": stats_urls["first_half"],
        "second_half": stats_urls["second_half"],
    }

    for period, stats_url in periods.items():
        try:
            print(f"Navigating to {period} statistics...")

            await page.goto(
                stats_url,
                wait_until="domcontentloaded"
            )

            await page.wait_for_selector(
                'div[data-testid="wcl-statistics"]',
                timeout=15000
            )

            period_stats = await parse_team_stats(
                page,
                home_team_id,
                away_team_id,
                period=period
            )

            print(f"DEBUG period requested: {period}")
            print(f"DEBUG periods returned: {set(s['period'] for s in period_stats)}")

            team_stats.extend(period_stats)

            print(
                f"{period}: collected "
                f"{len(period_stats)} statistic records"
            )

        except Exception as e:
            print(f"Could not collect {period} statistics: {e}")

    print("Total team statistic records:", len(team_stats))



    return {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,

        "home_score": home_goals,
        "away_score": away_goals,

        "match_date": match_date,
        "matchday": matchday,
        "match_status": match_status,

        "referee_id": referee_id,

        "season_id": season_id,
        "competition_id": competition_id,
        "stage_id": stage_id,

        "lineups": lineups,
        "events": events,
        "team_stats": team_stats,
        "player_stats": all_player_stats,

        "url": match_url,
        "stats_urls": stats_urls
        
    }


async def parse_lineups(page, home_team_id, away_team_id):

    lineups = []

    lineup_groups = await page.query_selector_all(
        "[data-testid='wcl-lineupsGroup']"
    )

    print(f"Found {len(lineup_groups)} lineup groups")

    for group in lineup_groups:

        # Read the lineup group header
        header = await get_text(
            group,
            "[data-testid='wcl-headerSection-text']"
        )

        print("Lineup group:", header)

        # Starting Lineups
        if "Starting Lineups" in header:
            starter = 1

        # Substitutes
        elif "Substitutes" in header:
            starter = 0

        else:
            continue

        # -------------------------
        # HOME TEAM
        # -------------------------

        home_players = await group.query_selector_all(
            "[data-testid='wcl-lineupsParticipantGeneral-left']"
        )

        print(f"Home players: {len(home_players)}")

        for player in home_players:

            player_name = await get_text(
                player,
                ".wcl-name_ZggyJ"
            )

            if not player_name:
                continue

            player_id = get_or_create_player(player_name)

            lineups.append({
                "team_id": home_team_id,
                "player_id": player_id,
                "position": None,
                "starter": starter,
                "substitutions": False,
                "formation_row": None,
                "formation_order": None,
                "rating": None
            })

            print(
                f"Home - {player_name} "
                f"(Player ID: {player_id}, Starter: {starter})"
            )

        # -------------------------
        # AWAY TEAM
        # -------------------------

        away_players = await group.query_selector_all(
            "[data-testid='wcl-lineupsParticipantGeneral-right']"
        )

        print(f"Away players: {len(away_players)}")

        for player in away_players:

            player_name = await get_text(
                player,
                ".wcl-name_ZggyJ"
            )

            if not player_name:
                continue

            player_id = get_or_create_player(player_name)

            lineups.append({
                "team_id": away_team_id,
                "player_id": player_id,
                "position": None,
                "starter": starter,
                "substitutions": False,
                "formation_row": None,
                "formation_order": None,
                "rating": None
            })

            print(
                f"Away - {player_name} "
                f"(Player ID: {player_id}, Starter: {starter})"
            )

    return lineups



async def inspect_team_stats(page, stats_url):
    await page.goto(stats_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

    print("\nSTATS URL:", page.url)

    html = await page.locator("body").inner_html()
    print(html[:12000])




def parse_stat_value(raw_value):
    if not raw_value:
        return None

    cleaned = raw_value.strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)

    if not match:
        return None

    return float(match.group())


async def get_primary_stat_value(element):
    return await element.evaluate("""
        el => Array.from(el.childNodes)
            .filter(node => node.nodeType === Node.TEXT_NODE)
            .map(node => node.textContent)
            .join("")
            .trim()
    """)



async def parse_team_stats(
    page,
    home_team_id,
    away_team_id,
    period="full_time"
):
    stats = []
    seen = set()

    stat_elements = await page.query_selector_all(
        'div[data-testid="wcl-statistics"]'
    )

    for stat in stat_elements:
        label_element = await stat.query_selector(
            '[data-testid="wcl-simple-text-01"], '
            '[data-testid="wcl-scores-heading-04"]'
        )

        if not label_element:
            continue

        label = (await label_element.inner_text()).strip()

        if not label or label in seen:
            continue

        home_element = await stat.query_selector(
            '.wcl-labelRow_42JBQ > div:first-child '
            '.wcl-value_Ywp3J'
        )

        away_element = await stat.query_selector(
            '.wcl-awayValue_smmfR .wcl-value_Ywp3J'
        )

        if not home_element or not away_element:
            continue

        home_raw = await get_primary_stat_value(home_element)
        away_raw = await get_primary_stat_value(away_element)

        home_value = parse_stat_value(home_raw)
        away_value = parse_stat_value(away_raw)

        if home_value is None or away_value is None:
            continue

        seen.add(label)

        stats.append({
            "team_id": home_team_id,
            "stat_name": label,
            "stat_value": home_value,
            "period": period,
        })

        stats.append({
            "team_id": away_team_id,
            "stat_name": label,
            "stat_value": away_value,
            "period": period,
        })

    return stats





async def parse_player_stats(page):
    player_stats = []

    table = page.locator('table[data-testid="wcl-table"]')

    if await table.count() == 0:
        print("Player statistics table not found.")
        return player_stats

    # Read the statistic column names
    headers = await table.locator(
        'thead th[data-testid="wcl-tableHeadCell"]'
    ).all()

    stat_names = []

    for header in headers:
        name = (await header.inner_text()).strip()
        stat_names.append(name)

    # Read each player's row
    rows = await table.locator(
        'tbody tr[data-testid="wcl-tableBodyRow"]'
    ).all()

    for row in rows:
        cells = await row.locator(
            'td[data-testid="wcl-tableBodyCell"]'
        ).all()

        if not cells:
            continue

        player_figure = cells[0].locator(
            '[data-testid="wcl-playerCell"]'
        )

        if await player_figure.count() == 0:
            continue

        player_external_id = await player_figure.get_attribute(
            "data-analytics-player-id"
        )

        name_element = player_figure.locator(
            '[data-testid="wcl-simple-text-02"]'
        )

        player_name = (
            (await name_element.inner_text()).strip()
            if await name_element.count()
            else ""
        )

        # Match each cell to its statistic header
        for index, cell in enumerate(cells[1:], start=1):
            if index >= len(stat_names):
                break

            stat_name = stat_names[index]
            raw_value = (await cell.inner_text()).strip()

            if not raw_value or raw_value in {"-", "—", "null", "NULL"}:
                # An unavailable rating must remain NULL, not zero.
                if stat_name.strip().lower() == "rating":
                    stat_value = None
                    stat_total = None

                else:
                    # For count-based stats, a dash represents zero activity.
                    stat_value = 0
                    stat_total = None

                player_stats.append({
                    "player_external_id": player_external_id,
                    "player_name": player_name,
                    "stat_name": stat_name,
                    "stat_value": stat_value,
                    "stat_total": stat_total,
                })

                continue

            # Remove percentage text, keeping the count or ratio
            raw_value = raw_value.split("(")[0].strip()

            stat_value = None
            stat_total = None

            if "/" in raw_value:
                parts = raw_value.split("/", 1)

                try:
                    stat_value = float(parts[0].strip())
                    stat_total = float(parts[1].strip())
                except ValueError:
                    continue
            else:
                try:
                    stat_value = float(raw_value.replace(",", ""))
                except ValueError:
                    continue

            player_stats.append({
                "player_external_id": player_external_id,
                "player_name": player_name,
                "stat_name": stat_name,
                "stat_value": stat_value,
                "stat_total": stat_total,
            })

    return player_stats





def save_team_stats(match_id, stats):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    try:
        for stat in stats:
            cursor.execute("""
                INSERT INTO team_stats (
                    match_id,
                    team_id,
                    stat_name,
                    stat_value,
                    period
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(match_id, team_id, stat_name, period)
                DO UPDATE SET
                    stat_value = excluded.stat_value
            """, (
                match_id,
                stat["team_id"],
                stat["stat_name"],
                stat["stat_value"],
                stat["period"]
            ))

        conn.commit()

    finally:
        conn.close()




def save_player_stats(match_id, player_stats):
    conn = sqlite3.connect("football.db")
    cursor = conn.cursor()

    saved = 0
    skipped = 0

    try:
        for stat in player_stats:
            player_name = stat["player_name"]

            # Find the player's internal ID through this match's lineup
            cursor.execute("""
                SELECT DISTINCT l.player_id, l.team_id
                FROM lineups l
                JOIN players p ON p.id = l.player_id
                WHERE l.match_id = ?
                  AND p.name = ?
            """, (match_id, player_name))

            matches = cursor.fetchall()

            # Only save if exactly one player matches
            if len(matches) != 1:
                print(
                    f"Skipping player stats for {player_name}: "
                    f"found {len(matches)} matching lineup records."
                )
                skipped += 1
                continue

            player_id, team_id = matches[0]

            cursor.execute("""
                INSERT INTO player_stats (
                    match_id,
                    player_id,
                    team_id,
                    stat_name,
                    stat_value,
                    stat_total
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id, player_id, stat_name)
                DO UPDATE SET
                    team_id = excluded.team_id,
                    stat_value = excluded.stat_value,
                    stat_total = excluded.stat_total
            """, (
                match_id,
                player_id,
                team_id,
                stat["stat_name"],
                stat["stat_value"],
                stat["stat_total"]
            ))

            saved += 1

        conn.commit()
        print(f"Player statistics saved: {saved}")
        print(f"Player statistics skipped: {skipped}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()



async def main():


    competition_id = get_or_create_competition("Super League")
    season_id = get_or_create_season("2026/2027")
    stage_id = None

    print("Competition ID:", competition_id)
    print("Season ID:", season_id)
    print("Stage ID:", stage_id)


    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(user_agent="Mozilla/5.0 (compatible; MyScraper/1.0)")

        print("Fetching match links...")
        match_links = await get_match_links(page, CHAMPIONSHIP_URL)
        print(f"Found {len(match_links)} matches")

        all_matches = []
        for i, link in enumerate(match_links):
            print(f"Scraping match {i+1}/{len(match_links)}: {link}")
            try:
                data = await parse_match(
                                page,
                                link,
                                competition_id,
                                season_id,
                                stage_id
                            )

                print("DEBUG records returned:", len(data["team_stats"]))
                print("DEBUG returned periods:", sorted({
                    stat["period"] for stat in data["team_stats"]
                }))

                match_id = save_match(data)
                print("Saved Match ID:", match_id)

                print("EVENTS FOUND:", len(data["events"]))
                print("EVENT DATA:", data["events"])

                print("Starting to save events...")
                save_events(match_id, data["events"])
                print("Events saved successfully!")


                save_lineups(match_id, data["lineups"])
                print("Lineups saved.")

                save_player_stats(match_id, data["player_stats"])

                print(
                    "Periods being saved:",
                    sorted({stat["period"] for stat in data["team_stats"]})
                )

                save_team_stats(match_id, data["team_stats"])
                print("Team statistics saved:", len(data["team_stats"]))

                all_matches.append(data)

            except Exception as e:
                print(f"Error scraping {link}: {e}")

        await browser.close()

if __name__ == "__main__":

    asyncio.run(main())

