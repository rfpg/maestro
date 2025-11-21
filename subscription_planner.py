#!/usr/bin/env python3
"""
Subscription Planner - Calculate how to maximize video generation
during your ChatGPT Pro subscription period
"""

from datetime import datetime, timedelta
import argparse


class SubscriptionPlanner:
    """Plan video generation to maximize ChatGPT Pro subscription value"""

    # Cost estimates (per second of video)
    COST_PER_SECOND = {
        "standard": 0.10,  # sora-2
        "pro": 0.30        # sora-2-pro
    }

    def __init__(self, budget: float, days_remaining: int):
        """
        Initialize planner

        Args:
            budget: Total budget in USD
            days_remaining: Days left in subscription
        """
        self.budget = budget
        self.days_remaining = days_remaining
        self.end_date = datetime.now() + timedelta(days=days_remaining)

    def calculate_max_videos(self, duration: int = 10, model: str = "standard") -> dict:
        """
        Calculate maximum number of videos possible

        Args:
            duration: Video duration in seconds
            model: Model type ('standard' or 'pro')

        Returns:
            Dictionary with planning details
        """
        cost_per_second = self.COST_PER_SECOND[model]
        cost_per_video = duration * cost_per_second

        max_videos = int(self.budget / cost_per_video)
        total_cost = max_videos * cost_per_video
        total_video_seconds = max_videos * duration
        total_video_minutes = total_video_seconds / 60
        total_video_hours = total_video_minutes / 60

        # Estimate generation time (80-90 seconds per video on average)
        avg_generation_time = 85  # seconds
        total_generation_time = max_videos * avg_generation_time
        generation_hours = total_generation_time / 3600
        generation_days = generation_hours / 24

        # Daily rate needed
        videos_per_day = max_videos / self.days_remaining if self.days_remaining > 0 else 0
        daily_budget = self.budget / self.days_remaining if self.days_remaining > 0 else 0

        return {
            "model": model,
            "duration_per_video": duration,
            "max_videos": max_videos,
            "total_cost": total_cost,
            "cost_per_video": cost_per_video,
            "remaining_budget": self.budget - total_cost,
            "total_video_seconds": total_video_seconds,
            "total_video_minutes": total_video_minutes,
            "total_video_hours": total_video_hours,
            "total_generation_hours": generation_hours,
            "total_generation_days": generation_days,
            "videos_per_day": videos_per_day,
            "daily_budget": daily_budget,
            "days_remaining": self.days_remaining,
            "end_date": self.end_date.strftime("%Y-%m-%d")
        }

    def print_plan(self, duration: int = 10, model: str = "standard"):
        """Print detailed subscription plan"""
        plan = self.calculate_max_videos(duration, model)

        print("\n" + "="*80)
        print("CHATGPT PRO SUBSCRIPTION - VIDEO GENERATION PLAN")
        print("="*80)
        print(f"\nSubscription Details:")
        print(f"  Days remaining:        {plan['days_remaining']} days")
        print(f"  Subscription ends:     {plan['end_date']}")
        print(f"  Total budget:          ${self.budget:,.2f}")
        print(f"  Daily budget:          ${plan['daily_budget']:.2f}/day")

        print(f"\nVideo Configuration:")
        print(f"  Model:                 {model} (sora-2{'-pro' if model == 'pro' else ''})")
        print(f"  Duration per video:    {duration} seconds")
        print(f"  Cost per video:        ${plan['cost_per_video']:.2f}")

        print(f"\nMaximum Output:")
        print(f"  Total videos:          {plan['max_videos']:,} videos")
        print(f"  Videos per day:        {plan['videos_per_day']:.1f} videos/day")
        print(f"  Total video content:   {plan['total_video_hours']:.1f} hours ({plan['total_video_minutes']:.0f} minutes)")

        print(f"\nGeneration Time Estimate:")
        print(f"  Total generation time: {plan['total_generation_hours']:.1f} hours ({plan['total_generation_days']:.1f} days)")
        print(f"  Note: Based on ~85 seconds per video generation")

        print(f"\nCost Summary:")
        print(f"  Total cost:            ${plan['total_cost']:,.2f}")
        print(f"  Remaining budget:      ${plan['remaining_budget']:.2f}")

        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)

        # Recommendations
        if plan['videos_per_day'] < 10:
            intensity = "Leisurely"
            recommendation = "You can comfortably generate videos at your own pace."
        elif plan['videos_per_day'] < 50:
            intensity = "Moderate"
            recommendation = "Plan daily batch generations to stay on track."
        elif plan['videos_per_day'] < 100:
            intensity = "Intensive"
            recommendation = "Consider running batch generations multiple times per day."
        else:
            intensity = "Very Intensive"
            recommendation = "This requires continuous generation. Consider reducing scope or extending timeline."

        print(f"\nPace:                  {intensity}")
        print(f"Advice:                {recommendation}")

        if plan['total_generation_days'] > plan['days_remaining']:
            print(f"\n⚠️  WARNING: Continuous generation would take {plan['total_generation_days']:.1f} days,")
            print(f"            but you only have {plan['days_remaining']} days remaining!")
            print(f"            You'll need to run multiple generation jobs in parallel.")

        print("\nSuggested Approach:")
        batch_size = min(20, max(5, int(plan['videos_per_day'])))
        batches_per_day = int(plan['videos_per_day'] / batch_size) + (1 if plan['videos_per_day'] % batch_size else 0)

        print(f"  1. Create {batch_size}-video batches")
        print(f"  2. Run {batches_per_day} batch(es) per day")
        print(f"  3. Use prompts file for automation")
        print(f"  4. Monitor API rate limits")
        print(f"  5. Review and adjust as needed")

        print("\n" + "="*80 + "\n")

    def compare_models(self, duration: int = 10):
        """Compare standard vs pro model options"""
        standard = self.calculate_max_videos(duration, "standard")
        pro = self.calculate_max_videos(duration, "pro")

        print("\n" + "="*80)
        print("MODEL COMPARISON")
        print("="*80)

        print(f"\n{'Metric':<30} {'Standard (sora-2)':<25} {'Pro (sora-2-pro)':<25}")
        print("-" * 80)
        print(f"{'Cost per video':<30} ${standard['cost_per_video']:<24.2f} ${pro['cost_per_video']:<24.2f}")
        print(f"{'Max videos':<30} {standard['max_videos']:<24,} {pro['max_videos']:<24,}")
        print(f"{'Videos per day':<30} {standard['videos_per_day']:<24.1f} {pro['videos_per_day']:<24.1f}")
        print(f"{'Total video hours':<30} {standard['total_video_hours']:<24.1f} {pro['total_video_hours']:<24.1f}")
        print(f"{'Generation time (days)':<30} {standard['total_generation_days']:<24.1f} {pro['total_generation_days']:<24.1f}")

        print("\n" + "="*80)
        print(f"💡 With Standard model, you get {(standard['max_videos'] / pro['max_videos']):.1f}x more videos!")
        print("="*80 + "\n")

    def create_milestone_schedule(self, duration: int = 10, model: str = "standard"):
        """Create a weekly milestone schedule"""
        plan = self.calculate_max_videos(duration, model)

        print("\n" + "="*80)
        print("WEEKLY MILESTONE SCHEDULE")
        print("="*80)

        weeks = (self.days_remaining + 6) // 7  # Round up to nearest week
        videos_per_week = plan['max_videos'] / weeks

        current_date = datetime.now()
        cumulative_videos = 0

        print(f"\n{'Week':<8} {'Date Range':<25} {'Videos':<15} {'Cumulative':<15} {'Cost':<15}")
        print("-" * 80)

        for week in range(1, weeks + 1):
            week_start = current_date + timedelta(days=(week-1)*7)
            week_end = min(week_start + timedelta(days=6), self.end_date)

            week_videos = int(videos_per_week)
            if week == weeks:
                week_videos = plan['max_videos'] - cumulative_videos

            cumulative_videos += week_videos
            week_cost = week_videos * plan['cost_per_video']

            date_range = f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"
            print(f"Week {week:<3} {date_range:<25} {week_videos:<15,} {cumulative_videos:<15,} ${week_cost:<14.2f}")

        print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Plan video generation strategy for ChatGPT Pro subscription"
    )
    parser.add_argument(
        '--budget',
        type=float,
        default=1000,
        help='Total budget in USD (default: 1000)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Days remaining in subscription (default: 30)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=10,
        help='Video duration in seconds (default: 10)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='standard',
        choices=['standard', 'pro'],
        help='Model to use (default: standard)'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare standard vs pro models'
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Show weekly milestone schedule'
    )

    args = parser.parse_args()

    planner = SubscriptionPlanner(budget=args.budget, days_remaining=args.days)

    # Show main plan
    planner.print_plan(duration=args.duration, model=args.model)

    # Show comparison if requested
    if args.compare:
        planner.compare_models(duration=args.duration)

    # Show schedule if requested
    if args.schedule:
        planner.create_milestone_schedule(duration=args.duration, model=args.model)


if __name__ == "__main__":
    main()
