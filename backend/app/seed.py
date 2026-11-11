"""Furnish the building before launch: staff rooms, basement secrets, elevator graffiti.

Run with `python -m app.seed` (also runs automatically on an empty database).
"""
import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import art
from .db import SessionLocal, init_db, utcnow
from .models import Floor, Graffiti
from .rooms import gate_for_pool, render_preview

R = random.Random


# (floor, name, message, wallpaper, objects, pixel factory)
ROOMS = [
    (1, "The First Floor", "Every building needs someone on the first floor to say hello. Hello. Take the stairs up if you like, I won't tell.", 0, [0, 5, 8], lambda: art.house().hex()),
    (2, "Two Plants, No Problems", "I water them on Sundays. They seem happy. I seem happy. That is the whole room.", 1, [0, 0 + 9, 1], lambda: art.flower(bg=1, petal=4).hex()),
    (3, "Third Time Lucky", "I tried to draw a horse twice. This is a sun. It went better.", 4, [5, 1], lambda: art.sunset().hex()),
    (7, "Lucky Seven", "Seven is the number of things I'd save in a fire. The cat counts as all seven.", 2, [2, 4, 1], lambda: art.cat_face().hex()),
    (10, "Double Digits", "Ten floors up. You can still hear the street. Someone is always whistling down there.", 3, [3, 5], lambda: art.city(R(10)).hex()),
    (12, "The Last Floor Before", "My landlord says there is no 13th floor above me. I hear footsteps anyway.", 10, [1, 7], lambda: art.ghost().hex()),
    (14, "Definitely Not 13", "This is floor 14. It has always been floor 14. Please stop asking.", 8, [7, 5], lambda: art.word("14", bg=12, fg=2, border=0).hex()),
    (21, "Blackjack Lounge", "Twenty-one. The house always wins, and this is my house, so I always win.", 9, [3, 5, 1], lambda: art.checker(a=2, b=0, size=4).hex()),
    (42, "The Answer", "I don't know the question either. I just liked the number. There's tea if you want some.", 10, [6, 1, 7], lambda: art.planet(R(42)).hex()),
    (50, "Top of the Street", "The last floor where you can still see people's faces from the window. After this they become dots.", 0, [0, 5, 3], lambda: art.tree().hex()),
    (77, "Seventy-Seven Sunsets", "I've watched seventy-seven sunsets from this window. I started counting this spring.", 7, [5, 1], lambda: art.sunset(sky=1, sun=3, hills=8, ground=0).hex()),
    (99, "Ninety-Nine Problems", "None of them are this room. This room is fine.", 5, [0, 4, 11], lambda: art.smiley().hex()),
    (100, "The Century Club", "Floor 100. I had a party when I moved in. Nobody came, because nobody had moved in yet.", 4, [3, 5, 6], lambda: art.word("100", bg=4, fg=2, border=0).hex()),
    (101, "Room 101", "There are no rats here. Just a very nice armchair and a lamp. You're safe.", 11, [5, 1], lambda: art.word("101", bg=11, fg=12).hex()),
    (123, "Easy As", "One, two, three. I wanted a room that was simple. This is it.", 3, [8, 5], lambda: art.stripes((9, 10, 11), 4, False).hex()),
    (200, "Two Hundred Club", "Halfway up the skyline band. Every night the city puts on its lights just for me (and everyone else).", 10, [11, 4], lambda: art.city(R(200), sky=8, glow=1).hex()),
    (222, "Angel Numbers", "Everyone says seeing 222 is a sign. I live here, so I see it all the time. Signs pending.", 6, [0, 1, 7], lambda: art.word("222", bg=6, fg=12, border=12).hex()),
    (256, "A Byte of a Room", "Two to the eighth. I keep things tidy in here, everything in its place, eight bits each.", 11, [11, 3], lambda: art.checker(a=8, b=11, size=2).hex()),
    (300, "Spartan Quarters", "One bed. One lamp. No complaints.", 8, [4, 1], lambda: art.stripes((2, 0), 2, False).hex()),
    (333, "Halfway to Mischief", "Three threes. I wanted 666 but they said it was too far to carry the sofa.", 1, [4, 2], lambda: art.mushroom().hex()),
    (365, "One Year", "I promised myself I'd come back to this room once a day for a year. Day one.", 0, [7, 0, 5], lambda: art.word("365", bg=12, fg=9, border=9).hex()),
    (451, "Paper Room", "The temperature at which books burn. All my books are safe in here. Mostly.", 7, [6, 1, 5], lambda: art.word("451", bg=3, fg=0, border=2).hex()),
    (500, "Top of the Skyline", "From here you can see where the city ends and the clouds start. They are closer than you'd think.", 3, [5, 1], lambda: art.mountains().hex()),
    (512, "Half a K", "Every five hundred and twelfth day I repaint the walls. Sky blue again.", 3, [0, 11], lambda: art.stripes((10, 11, 12), 3).hex()),
    (555, "The Fives", "I asked for floor 555 because it looks like someone laughing in Thai. Hahaha.", 4, [2, 3], lambda: art.smiley(bg=2).hex()),
    (600, "Cloud Level", "First floor in the clouds. Sometimes I open the window and the room fills with fog.", 3, [4, 0], lambda: art.rainbow().hex()),
    (700, "Mist Apartment", "Everything in here is slightly damp. The plant loves it.", 5, [0, 0 + 9], lambda: art.waves(sky=13, sea=7, deep=8).hex()),
    (777, "Jackpot", "Three sevens. I won the floor lottery. Sit anywhere.", 4, [11, 3, 5], lambda: art.word("777", bg=0, fg=4, border=2).hex()),
    (808, "Drum Machine", "Boom. Tss. Boom-boom. Tss. My neighbours are very patient.", 10, [3, 10, 11], lambda: art.stripes((1, 2, 3, 4), 2, False).hex()),
    (888, "Lucky Eights", "Eight is lucky where my family is from. Three eights is lucky enough to last.", 2, [0, 1, 7], lambda: art.word("888", bg=2, fg=4, border=4).hex()),
    (900, "Weather Station", "I keep a log of every cloud that passes the window. Today: four. Fluffy, mostly.", 3, [7, 3], lambda: art.sunset(sky=10, sun=12, hills=13, ground=14).hex()),
    (1000, "The Thousandth Floor", "A thousand floors up. You'd think it'd feel special. It does. Leave a note so I know you came.", 4, [5, 1, 8], lambda: art.word("1000", bg=8, fg=4, border=4).hex()),
    (1024, "Kilobyte Cottage", "Exactly one kilo of floor. The pixels on my wall are all 1024 of them. I counted.", 11, [11, 6, 5], lambda: art.checker(a=0, b=5, size=8).hex()),
    (1111, "Make a Wish", "It's always 11:11 somewhere. Here, it's always floor 1111. Make one.", 6, [1, 4], lambda: art.night_sky(R(1111), bg=1).hex()),
    (1200, "Kite Room", "On windy days I fly a kite out of the window. It's never come back down.", 3, [5, 0], lambda: art.waves(sky=10, sea=12, deep=13, foam=11).hex()),
    (1500, "Midway Cafe", "Coffee is free. The view is free. The chairs are free but please don't take them.", 0, [5, 3, 0], lambda: art.coffee().hex()),
    (1984, "Not Watching", "There is no camera in this room. There is, however, a very judgemental cat.", 11, [2, 11], lambda: art.word("1984", bg=14, fg=12).hex()),
    (2000, "Y2K Bunker", "Stocked with canned beans since 1999. Nothing happened. I'm keeping the beans.", 8, [3, 11, 6], lambda: art.word("Y2K", bg=0, fg=5, border=5).hex()),
    (2048, "Slide Puzzle", "I got to 2048 once. Then I moved here. Haven't played since.", 4, [5, 1], lambda: art.checker(a=4, b=3, size=8).hex()),
    (2222, "Twos All the Way Down", "Four twos. A room for people who like things to come in pairs.", 6, [2, 2 + 3], lambda: art.heart(bg=6, fg=2).hex()),
    (2417, "Say It Out Loud", "I live on floor 2,417. Say it out loud. Feels good, right? Claim yours and you'll see.", 1, [4, 1, 2], lambda: art.word("2417", bg=1, fg=4, border=4).hex()),
    (2500, "Cloud Gardener", "I grow plants on the clouds outside. They grow sideways. It's a whole thing.", 1, [0, 0 + 9, 5], lambda: art.cactus().hex()),
    (3000, "Edge of the Clouds", "Above here the sky starts turning dark. I like being on the edge of things.", 10, [1, 6], lambda: art.sunset(sky=8, sun=11, hills=9, ground=10).hex()),
    (3141, "Pi Room", "3.141. Every pie in here is round. I'm told this is the point.", 7, [5, 7], lambda: art.spiral().hex()),
    (3333, "High Altitude Choir", "The air is thin and every note I sing comes out a little higher. Come sing.", 6, [10, 3], lambda: art.word("LA LA", bg=6, fg=12).hex()),
    (4000, "Thin Air", "You can see the curve of the earth from here if you squint. I squint a lot.", 10, [1, 4], lambda: art.planet(R(4000), body=9, ring=12).hex()),
    (4096, "Four K", "Ultra high definition living. Every speck of dust in 4K.", 8, [11, 5], lambda: art.checker(a=9, b=10, size=4).hex()),
    (4444, "Four Corners", "Four fours. Four walls. Four houseplants. One very tidy person.", 1, [0, 0 + 6, 8], lambda: art.stripes((6, 5, 7, 12), 4).hex()),
    (5000, "Halfway House", "Exactly halfway up the building. Downstairs it's day. Upstairs it's night. I get both.", 6, [4, 1, 7], lambda: art.night_sky(R(5000), bg=8).hex()),
    (5555, "High Fives", "Floor of the four fives. Every visitor gets a high five. Consider yourself fived.", 4, [3, 5], lambda: art.heart(bg=4, fg=3).hex()),
    (6000, "Satellite Spotter", "Every 90 minutes a satellite passes the window. I wave. Unconfirmed if they wave back.", 10, [11, 6], lambda: art.planet(R(6000), body=6, ring=4).hex()),
    (6502, "Old Processor", "Named after a little chip that ran a lot of old computers. Still runs this room.", 9, [11, 3], lambda: art.word("6502", bg=9, fg=12, border=12).hex()),
    (7000, "Quiet Room", "Please whisper. Not because of rules. It just feels like a whispering kind of floor.", 10, [1, 4], lambda: art.waves(sky=8, sea=1, deep=0, foam=9).hex()),
    (7777, "Four Sevens", "The luckiest floor in the building. If you're reading this, some of it rubbed off on you.", 4, [11, 1, 0], lambda: art.word("7777", bg=2, fg=4, border=4).hex()),
    (8000, "Night Shift", "It's always night up here. I keep a lamp on for whoever comes by.", 10, [1, 5, 4], lambda: art.city(R(8000), sky=0, glow=8).hex()),
    (8080, "Port 8080", "Local development apartment. Everything works here and nowhere else.", 11, [11, 5], lambda: art.word("8080", bg=0, fg=5).hex()),
    (8192, "Memory Lane", "Two to the thirteenth. Funny, given what floor they skipped.", 6, [6, 7], lambda: art.stripes((1, 8, 9, 10), 2).hex()),
    (8888, "Infinity Sideways", "Eight is infinity standing up. Four of them is a lot of forever.", 2, [4, 1], lambda: art.word("8888", bg=1, fg=11, border=11).hex()),
    (9000, "Over Nine Thousand", "Yes. It's over nine thousand. Happy now? The stars start just above.", 10, [5, 11], lambda: art.word("9000", bg=0, fg=3, border=2).hex()),
    (9001, "First Star Floor", "The first floor where you can see stars all day. I named one after you. It's that one.", 10, [4, 1], lambda: art.night_sky(R(9001), bg=0, moon=12).hex()),
    (9500, "Observatory", "There's a telescope in the corner. Point it anywhere. Everything is up here.", 10, [5, 7], lambda: art.planet(R(9500), body=1, ring=11).hex()),
    (9876, "Countdown", "Nine, eight, seven, six. Liftoff is somewhere near floor 10,000.", 11, [7, 3], lambda: art.word("9876", bg=8, fg=12).hex()),
    (9999, "The Penthouse (Sort Of)", "One floor below the roof. I can hear people stargazing upstairs. They clap at meteors.", 10, [4, 1, 6], lambda: art.night_sky(R(9999), bg=1, moon=4).hex()),
    (31, "The Aquarium", "I keep three goldfish and a very old turtle. The turtle owns the room. I just rent it.", 3, [9, 0, 8], lambda: art.fish().hex()),
    (64, "Sixty-Four Squares", "A chessboard, a kettle and an open invitation. White moves first.", 0, [5, 1], lambda: art.checker(a=0, b=12, size=4).hex()),
    (88, "Piano Room", "Eighty-eight keys on the piano, eighty-eight on this floor. Play something.", 10, [10, 1, 5], lambda: art.stripes((12, 12, 0), 3, False).hex()),
    (144, "A Gross Room", "A gross is 144. This room is not gross. It is, in fact, very clean.", 5, [8, 0], lambda: art.mushroom(bg=5, cap=9).hex()),
    (360, "Full Circle", "I left home, travelled a lot, and ended up here, which feels like home. Full circle.", 6, [8, 7, 0], lambda: art.spiral(bg=8, fg=4).hex()),
    (420, "Greenhouse", "Too many plants. Not enough window. The plants are winning.", 1, [0, 0 + 9], lambda: art.tree(bg=5, leaves=7).hex()),
    (1001, "A Thousand and One Nights", "One story per visitor. Leave the start of one in a note and someone else will finish it.", 1, [8, 1, 3], lambda: art.night_sky(R(1001), bg=1, moon=3).hex()),
]

BASEMENT = [
    (-1, "I've been pretending to understand my job for three years. Nobody has noticed. I think everyone else is too."),
    (-3, "I still sleep with the light on. I'm thirty-four."),
    (-7, "I told my best friend I loved their cooking. I have been eating it for six years. I do not love their cooking."),
    (-12, "Sometimes I take the long way home just to sit in the car a bit longer before I have to be a person again."),
    (-20, "I've never seen a single film everyone says is a classic. I just nod."),
    (-33, "I miss someone I'm not allowed to miss anymore."),
    (-44, "I sing in the shower in a fake accent so nobody recognises my voice. I live alone."),
    (-50, "I moved cities to start over. It worked. I'm happier than I've ever been and I haven't told anyone back home."),
    (-66, "I keep every birthday card I've ever been given in a shoebox. I read them when the days are bad."),
    (-77, "I'm scared that I peaked at nineteen. I'm also scared that I didn't and this is it."),
    (-88, "I laughed at a funeral once. The person in the coffin would have laughed too."),
    (-99, "I wrote a letter to my younger self. I haven't decided if it's a warning or an apology."),
    (-100, "This is the bottom of the building. If you made it all the way down here, you're curious. Good. Stay that way."),
]

GRAFFITI = [
    "was here", "floor 13 is real", "the music never stops", "hi from floor 9001",
    "who keeps pressing every button", "ride count: way too many", "it's always night up top",
    "the basement bulb winked at me", "say hello to the cat on 7", "lift goes brr",
    "try the dice", "tell your friends", "someone left a kettle on 7½",
    "i got stuck once. worth it", "the roof has the best view", "love you whoever reads this",
    "404 isn't a joke, it's a wall", "do NOT go to B100 alone", "this elevator smells like pennies",
    "next stop: somewhere",
]


def seed(db: Session) -> int:
    if db.scalar(select(func.count()).select_from(Floor)):
        return 0
    now = utcnow()
    count = 0
    for i, (n, name, message, wallpaper, objects, factory) in enumerate(ROOMS):
        objs = list(dict.fromkeys(o % 12 for o in objects))[:3]
        f = Floor(number=n, name=name, message=message, pixels=factory(), wallpaper=wallpaper,
                  objects=objs, is_staff=True, status="live",
                  visit_count=random.Random(n).randrange(3, 120),
                  created_at=now - timedelta(days=30 - i % 30), updated_at=now,
                  last_visited_at=now, owner_seen_at=now)
        gate_for_pool(f, now)
        render_preview(f)
        db.add(f)
        count += 1
    for n, message in BASEMENT:
        f = Floor(number=n, message=message, is_staff=True, status="live",
                  created_at=now - timedelta(days=20), updated_at=now,
                  last_visited_at=now, owner_seen_at=now)
        gate_for_pool(f, now)
        render_preview(f)
        db.add(f)
        count += 1
    for i, body in enumerate(GRAFFITI):
        db.add(Graffiti(body=body, created_at=now - timedelta(hours=len(GRAFFITI) - i)))
    db.commit()
    return count


if __name__ == "__main__":
    init_db()
    with SessionLocal() as s:
        print(f"Seeded {seed(s)} floors.")
