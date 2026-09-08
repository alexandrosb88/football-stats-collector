import asyncio
import pandas as pd
import re
import sqlite3
from playwright.async_api import async_playwright
import os
from datetime import datetime

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
                minute,
                added_time,
                period,
                event_type,
                event_detail,
                home_score,
                away_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            event["team_id"],
            event["player_id"],
            event["second_player_id"],
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

    home_incidents = (await page.query_selector_all("div.smv__participantRow.smv__homeParticipant"))
    print(f"Found {len(home_incidents)} home incidents")


    for incident in home_incidents:

        time = await get_text(incident, "div.smv__timeBox")
        player = await get_text(incident, "a.smv__playerName")
        player_out = await get_text(
            incident,
            "a.smv__subDown.smv__playerName"
        )

        svg_title = await get_text(
            incident,
            "div.smv__incidentIcon svg title"
        )

        svg_title_substitution = await get_text(
            incident,
            "div.smv__incidentIconSub svg title"
        )

        if "Yellow Card" in svg_title:

            print(f"{time} - Yellow Card - {player}")

            yellow_card_counter += 1

            events.append({
                "team_id": home_team_id,
                "player_id": None,
                "second_player_id": None,
                "minute": time,
                "added_time": None,
                "period": None,
                "event_type": "card",
                "event_detail": "yellow",
                "home_score": home_goals,
                "away_score": away_goals
            })

        elif "Red Card" in svg_title:

            print(f"{time} - Red Card - {player}")

            red_card_counter += 1

            events.append({
                "team_id": home_team_id,
                "player_id": None,
                "second_player_id": None,
                "minute": time,
                "added_time": None,
                "period": None,
                "event_type": "card",
                "event_detail": "red",
                "home_score": home_goals,
                "away_score": away_goals
            })

        elif "Substitution" in svg_title_substitution:

            print(
                f"{time} - player in {player} - player out {player_out}"
            )

            events.append({
                "team_id": home_team_id,
                "player_id": None,
                "second_player_id": None,
                "minute": time,
                "added_time": None,
                "period": None,
                "event_type": "substitution",
                "event_detail": None,
                "home_score": home_goals,
                "away_score": away_goals
            })

                
    away_incidents = await page.query_selector_all(
    "div.smv__participantRow.smv__awayParticipant"
)

    print(f"Found {len(away_incidents)} away incidents")

    for incident in away_incidents:

        time = await get_text(incident, "div.smv__timeBox")
        player = await get_text(incident, "a.smv__playerName")
        player_out = await get_text(
            incident,
            "a.smv__subDown.smv__playerName"
        )

        svg_title = await get_text(
            incident,
            "div.smv__incidentIcon svg title"
        )

        svg_title_substitution = await get_text(
            incident,
            "div.smv__incidentIconSub svg title"
        )

        if "Yellow Card" in svg_title:

            print(f"{time} - Yellow Card - {player}")

            yellow_card_counter += 1

            events.append({
                "team_id": away_team_id,
                "player_id": None,
                "second_player_id": None,
                "minute": time,
                "added_time": None,
                "period": None,
                "event_type": "card",
                "event_detail": "yellow",
                "home_score": home_goals,
                "away_score": away_goals
            })

        elif "Red Card" in svg_title:

            print(f"{time} - Red Card - {player}")

            red_card_counter += 1

            events.append({
                "team_id": away_team_id,
                "player_id": None,
                "second_player_id": None,
                "minute": time,
                "added_time": None,
                "period": None,
                "event_type": "card",
                "event_detail": "red",
                "home_score": home_goals,
                "away_score": away_goals
            })

        elif "Substitution" in svg_title_substitution:

            print(
                f"{time} - player in {player} - player out {player_out}"
            )

            events.append({
                "team_id": away_team_id,
                "player_id": None,
                "second_player_id": None,
                "minute": time,
                "added_time": None,
                "period": None,
                "event_type": "substitution",
                "event_detail": None,
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

    # Stats — navigate to the dedicated stats subpage
    match_stats = {}
    try:
        base_url = match_url.split("?")[0].rstrip("/")
        mid = match_url.split("mid=")[-1] if "mid=" in match_url else ""
        stats_url = f"{base_url}/summary/stats/overall/" + (f"?mid={mid}" if mid else "")

        print(f"Navigating to stats page: {stats_url}")
        await page.goto(stats_url, wait_until="domcontentloaded")
        await page.wait_for_selector("[data-testid='wcl-statistics-item']", timeout=8000)

        stat_rows = await page.query_selector_all("[data-testid='wcl-statistics-item']")
        print(f"Found {len(stat_rows)} stat rows")

        for row in stat_rows:
            category_el = await row.query_selector(
                "[data-testid='wcl-statistics-category'] [data-testid='wcl-scores-simple-text-01']"
            )
            category = (await category_el.text_content()).strip() if category_el else ""

            value_els = await row.query_selector_all("[data-testid='wcl-statistics-value'] span")
            home_val = (await value_els[0].text_content()).strip() if len(value_els) > 0 else ""
            away_val = (await value_els[1].text_content()).strip() if len(value_els) > 1 else ""

            if category:
                match_stats[category] = {"home": home_val, "away": away_val}
                print(f"  {category}: home={home_val} away={away_val}")

    except Exception as e:
        print(f"Stats error: {e}")


    # Team stats
    stats = {}
    for row in await page.query_selector_all("table.team-stats tr"):
        try:
            cells = await row.query_selector_all("td")
            if len(cells) >= 3:
                stat_name = (await cells[1].text_content()).strip()
                stats[stat_name] = {
                    "home": (await cells[0].text_content()).strip(),
                    "away": (await cells[2].text_content()).strip()
                }
        except:
            continue

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

        "events": events,
        "stats": stats,

        "url": match_url
    }

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

                match_id = save_match(data)
                print("Saved Match ID:", match_id)

                save_events(match_id, data["events"])
                print("Events saved.")

                all_matches.append(data)

            except Exception as e:
                print(f"Error scraping {link}: {e}")

        await browser.close()

    # Flatten for CSV
    rows = []
    for match in all_matches:
        base = {
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "score": match["score"],
            "referee": match["referee"],
            "url": match["url"]
        }
        for ev in match["events"]:
            row = base.copy()
            row.update({
                "event_minute": ev["minute"],
                "event_player": ev["player"],
                "event_detail": ev["detail"]
            })
            for stat_name, vals in match["stats"].items():
                row[f"{stat_name}_home"] = vals["home"]
                row[f"{stat_name}_away"] = vals["away"]
            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(CSV_FILE, index=False)
    print(f"Saved to {CSV_FILE}")

if __name__ == "__main__":

    asyncio.run(main())

