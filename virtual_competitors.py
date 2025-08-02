import random
from datetime import timedelta

def generate_competitor_profiles(user_duration_min, user_avg_speed, num_competitors=3):
    strategies = ["even", "positive_split", "negative_split", "mid_surge", "random"]
    competitors = []
    for i in range(num_competitors):
        variation = random.uniform(-0.025, 0.025)  # ±2.5% duration variation
        comp_time = user_duration_min * (1 + variation)
        comp_avg_speed = user_avg_speed * (user_duration_min / comp_time)  # Maintain same distance
        print(f"A ghost time is: {comp_time:.2f} min, with expected average speed of: {comp_avg_speed:.2f} km\n")
        strategy = random.choice(strategies)
        competitors.append({
            "name": f"Ghost {chr(65+i)}",
            "duration_min": comp_time,
            "avg_speed": comp_avg_speed,
            "strategy": strategy
        })
    return competitors

def normalize_speed_profile(speed_profile, target_avg, segment_duration_sec):
    total_distance = compute_total_distance(speed_profile, segment_duration_sec)
    expected_distance = target_avg * (segment_duration_sec * len(speed_profile) / 3600.0)
    scale = expected_distance / total_distance
    return [(t, speed * scale) for t, speed in speed_profile]

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

    return normalize_speed_profile(speed_profile, avg_speed, segment_duration)

def compute_total_distance(speed_profile, segment_duration_sec):
    total = 0.0
    for _, speed in speed_profile:
        total += speed * (segment_duration_sec / 3600.0)  # Convert to km
    return total

def generate_competitors_with_profiles(user_duration_min, user_avg_speed, num_competitors=3):
    competitors = generate_competitor_profiles(user_duration_min, user_avg_speed, num_competitors)
    for competitor in competitors:
        duration_min = competitor["duration_min"]
        strategy = competitor["strategy"]
        avg_speed = competitor["avg_speed"]

        speed_profile = generate_speed_profile(duration_min, avg_speed, strategy)
        competitor["speed_profile"] = speed_profile

        # ➕ Add time difference to name
        time_diff_sec = (duration_min - user_duration_min) * 60
        if abs(time_diff_sec) < 1:
            delta_str = "±0s"
        elif time_diff_sec > 0:
            delta_str = f"+{int(round(time_diff_sec))}s"
        else:
            delta_str = f"{int(round(time_diff_sec))}s"

        competitor["base_name"] = competitor["name"]

    return competitors

if __name__ == "__main__":
    user_duration_min = 33
    user_avg_speed = 10.0  # km/h
    user_distance = user_avg_speed * (user_duration_min / 60.0)

    competitors = generate_competitors_with_profiles(user_duration_min, user_avg_speed)

    print(f"User target: {user_duration_min:.2f} min, Distance: {user_distance:.2f} km\n")

    for competitor in competitors:
        name = competitor["name"]
        duration = competitor["duration_min"]
        avg_speed = competitor["avg_speed"]
        strategy = competitor["strategy"]
        speed_profile = competitor["speed_profile"]
        segment_duration = (duration * 60) / len(speed_profile)
        total_distance = compute_total_distance(speed_profile, segment_duration)

        print(f"Competitor: {name}")
        print(f"  Strategy: {strategy}")
        print(f"  Target Duration: {duration:.2f} min")
        print(f"  Target Distance: {total_distance:.2f} km")
        print("  Speed Profile:")
        for timestamp, speed in speed_profile:
            print(f"    {str(timedelta(seconds=timestamp))} — {speed:.2f} km/h")
        print()
