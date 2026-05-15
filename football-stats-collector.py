import asyncio
import pandas as pd
from playwright.async_api import async_playwright

# CONFIG — change this to your league/championship page
CHAMPIONSHIP_URL = "https://www.soccerway.com/greece/super-league/results/"  # ← replace with actual URL
CSV_FILE = "superleague_stats.csv"



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
        "a[href*='/match/']",
        "els => els.map(el => el.href)"
    )

    print(links)

    return list(set(links))


  

async def parse_match(page, match_url, referee_stats):
    await page.goto(match_url, wait_until="networkidle")

    # Teams
    home_team = (await page.get_attribute("div.duelParticipant__home img.participant__image",
    "alt")) or ""
    away_team = (await page.get_attribute("div.duelParticipant__away img.participant__image",
    "alt")) or ""

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
    
    
    home_incidents = (await page.query_selector_all("div.smv__participantRow.smv__homeParticipant"))
    print(f"Found {len(home_incidents)} home incidents")


    for incident in home_incidents:

                print("\n entering home incidents loop")

                time = await get_text(incident, "div.smv__timeBox")
                player = await get_text(incident, "a.smv__playerName")
                player_out = await get_text(incident, "a.smv__subDown.smv__playerName")
                svg_title = await get_text(incident, "div.smv__incidentIcon svg title")
                svg_title_substitution = await get_text(incident, "div.smv__incidentIconSub svg title")


                if "Yellow Card" in svg_title:
                    print(f"{time} - Yellow Card - {player}")
                    yellow_card_counter +=1
                    print(yellow_card_counter)

                elif "Red Card" in svg_title:
                    print(f"{time} - Red Card - {player}")
                    red_card_counter +=1
                    print(red_card_counter)

                elif "Substitution" in svg_title_substitution:
                    print(f"{time} - player in {player} - player out {player_out}")

                
                          

    # Referee
    referee = ""
    try:
        referee = (await get_text(page, "div.wcl-infoValue_grawU"))
        referee = referee.replace("\xa0", " ").strip()

        print("Referee: ", referee)

        if referee not in referee_stats:
            referee_stats[referee] = {"games": 0, "yellow": 0, "red": 0}

        referee_stats[referee]["games"] += 1
        referee_stats[referee]["yellow"] += yellow_card_counter
        referee_stats[referee]["red"] += red_card_counter


        for ref, stats in referee_stats.items():
            print(f"{ref}: {stats['games']} games, {stats['yellow']} yellows, {stats['red']} reds")

        
    except:
        pass

    # Events (goals, cards, etc.)
    events = []
    # Example: rows in a container of events
    for row in await page.query_selector_all("div.events-container tr"):
        try:
            minute = await row.query_selector_eval("td.minute", "el => el.innerText")
            player = await row.query_selector_eval("td.player", "el => el.innerText")
            detail = await row.query_selector_eval("td.event-type", "el => el.innerText")
            events.append({"minute": minute.strip(), "player": player.strip(), "detail": detail.strip()})
        except:
            continue

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
        "home_team": home_team.strip(),
        "away_team": away_team.strip(),
        "score": score.strip(),
        "referee": referee,
        "events": events,
        "stats": stats,
        "url": match_url
    }

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (compatible; MyScraper/1.0)")

        print("Fetching match links...")
        match_links = await get_match_links(page, CHAMPIONSHIP_URL)
        print(f"Found {len(match_links)} matches")

        referee_stats = {}

        all_matches = []
        for i, link in enumerate(match_links):
            print(f"Scraping match {i+1}/{len(match_links)}: {link}")
            try:
                data = await parse_match(page, link, referee_stats)
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
