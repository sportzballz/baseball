import os

from openai import OpenAI


def get_pick_summary(predictions, model_name):
    """
    Send today's picks to an LLM and get back a summary with a pick-of-the-day suggestion.

    Args:
        predictions: list of Prediction objects (already filtered to valid picks)
        model_name: name of the model that generated the picks (e.g. 'ashburn')

    Returns:
        str: LLM-generated summary and pick-of-the-day suggestion
    """
    if not predictions:
        return "No valid picks today."

    picks_text = "\n".join(
        f"- {p.winning_team} over {p.losing_team} | "
        f"Odds: {p.odds} | Confidence: {p.confidence} | "
        f"Data Points: {p.data_points} | "
        f"Pitchers: {p.winning_pitcher} vs {p.losing_pitcher} | "
        f"Game Time: {p.gameTime}{p.ampm}"
        for p in predictions
        if p.winning_team != '-'
    )

    if not picks_text:
        return "No valid picks today."

    system_prompt = (
        f"You are an expert MLB baseball analyst. You are given a set of model-generated "
        f"picks for today's games produced by the '{model_name}' prediction model. "
        f"Each pick includes the predicted winner, moneyline odds, model confidence "
        f"(0-1 scale, higher is better), data points (winner points / total points), "
        f"starting pitchers, and game time.\n\n"
        f"Provide:\n"
        f"1. A brief summary of all today's picks\n"
        f"2. Your PICK OF THE DAY — the single best bet with a short explanation of why "
        f"it stands out (consider confidence, odds value, and pitching matchup)\n"
        f"3. Any picks to avoid or that look risky\n\n"
        f"Keep the response concise and suitable for posting in a Slack channel."
    )

    user_prompt = (
        f"Here are today's picks from the {model_name} model:\n\n{picks_text}\n\n"
        f"What's your summary and pick of the day?"
    )

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
