import random
from datetime import timedelta

def generate_competitor_profiles(user_duration_min, user_avg_speed, num_competitors=3):
    strategies = ["even", "positive_split", "negative_split", "mid_surge", "random"]
    competitors = []
    for i in range(num_competitors):
        variation = random.uniform(-0.025, 0.025)  # ±5% duration variation
        comp_time = user_duration_min * (1 + variation)
        comp_avg_speed = user_avg_speed * (user_duration_min / comp_time)  # Adjust speed to match new time
        strategy = random.choice(strategies)
        competitors.append({
            "name": f"Ghost {chr(65+i)}",
            "duration_min": comp_time,
            "avg_speed": comp_avg_speed,
            "strategy": strategy
        })
    return competitors

def generate_speed_profile(duration_min, avg_speed, strategy):
    segments = 10
    segment_duration = duration_min * 60 / segments
    speed_profile = []

    if strategy == "even":
        for i in range(segments):
            speed_profile.append((i * segment_duration, avg_speed))
    elif strategy == "positive_split":
        for i in range(segments):
            speed = avg_speed + (i / segments) * (avg_speed * 0.2)
            speed_profile.append((i * segment_duration, speed))
    elif strategy == "negative_split":
        for i in range(segments):
            speed = avg_speed - (i / segments) * (avg_speed * 0.2)
            speed_profile.append((i * segment_duration, speed))
    elif strategy == "mid_surge":
        for i in range(segments):
            speed = avg_speed * 1.2 if segments // 3 <= i < 2 * segments // 3 else avg_speed
            speed_profile.append((i * segment_duration, speed))
    elif strategy == "random":
        for i in range(segments):
            speed = random.uniform(avg_speed * 0.8, avg_speed * 1.2)
            speed_profile.append((i * segment_duration, speed))

    return speed_profile

def generate_competitors_with_profiles(user_duration_min, user_avg_speed, num_competitors=3):
    competitors = generate_competitor_profiles(user_duration_min, user_avg_speed, num_competitors)
    for competitor in competitors:
        competitor["speed_profile"] = generate_speed_profile(
            competitor["duration_min"],
            competitor["avg_speed"],
            competitor["strategy"]
        )
    return competitors

if __name__ == "__main__":
    user_duration_min = 30
    user_avg_speed = 10.0
    competitors = generate_competitors_with_profiles(user_duration_min, user_avg_speed)
    for competitor in competitors:
        print(f"Competitor: {competitor['name']}")
        print(f"Duration: {competitor['duration_min']:.2f} min")
        print(f"Average Speed: {competitor['avg_speed']:.2f} km/h")
        print(f"Strategy: {competitor['strategy']}")
        print("Speed Profile:")
        for timestamp, speed in competitor["speed_profile"]:
            print(f"{str(timedelta(seconds=timestamp))} — {speed:.2f} km/h")
        print()
