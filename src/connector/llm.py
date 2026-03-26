import os

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate


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

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert MLB baseball analyst. You are given a set of model-generated "
         "picks for today's games produced by the '{model_name}' prediction model. "
         "Each pick includes the predicted winner, moneyline odds, model confidence "
         "(0-1 scale, higher is better), data points (winner points / total points), "
         "starting pitchers, and game time.\n\n"
         "Provide:\n"
         "1. A brief summary of all today's picks\n"
         "2. Your PICK OF THE DAY — the single best bet with a short explanation of why "
         "it stands out (consider confidence, odds value, and pitching matchup)\n"
         "3. Any picks to avoid or that look risky\n\n"
         "Keep the response concise and suitable for posting in a Slack channel."
         ),
        ("human",
         "Here are today's picks from the {model_name} model:\n\n{picks}\n\n"
         "What's your summary and pick of the day?"
         ),
    ])

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    chain = prompt | llm
    response = chain.invoke({
        "model_name": model_name,
        "picks": picks_text,
    })

    return response.content
