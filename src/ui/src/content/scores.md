# Scoring

The scoring system used in this challenge is designed around the following three principles: 
- For each level, points are assigned to teams according to the order in which the teams solved the level. 
- For each level, points are adjusted based on the difficulty of the level, as represented by the number of teams that solved the level.  
- To break ties (if any), teams with the same score will be ordered based on the average of the timestamps for the first successful solution they provided to each level. 

## Order 

Each level starts with a base score = 40000 points. All teams that provide a successful solution for the level will be ordered based on the timestamp of their first successful solution and will receive an order_adjusted_score calculated as follows: 

```
order_adjusted_score = max(min threshold, base score ∗ β**i),
```

where β = 0.95, i ∈ 0, 1, ..., n is the rank order of the team’s submission (i.e., i = 0 is the first team to solve the level), and min threshold = 30000. 

## Difficulty 

Scores for each level are scaled based on the number of teams that successfully solved the level. Each time a new team submits their first correct solution for a level, the scores of all teams for that level are adjusted as follows: 
```
difficulty_adjusted_score = order_adjusted_score ∗ γ**solves, 
```
where γ = 0.85 and solves is the total number of teams that successfully solved this level. This means that more points are awarded for solving more difficult levels. 

A team’s total_score is the sum of their difficulty_adjusted_score for each level they successfully solved. The total_score will be used to determine the final ranking of teams. 

## Average order of solves 

If there are any ties within the top four places (i.e., the four teams with the highest total scores), we will compute the average of the timestamps of the first successful solution for each level the team solved. The team with the lower timestamp will win the tie (i.e., this team on average solved all the levels they solved first). Note that this does not normally affect the team’s total_score, but is only used to break ties.
