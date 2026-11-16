"""Family-cluster intervals; never resample translations/repeats as new tasks."""
import random
from collections import defaultdict
from statistics import mean


def point(tasks,track):
    if track!='B':return mean(row['score'] for row in tasks)
    skills=defaultdict(list)
    for row in tasks:skills[row['skill']].append(row['score'])
    return mean(mean(scores) for scores in skills.values())


def interval(tasks,track,draws=2000,seed=20261112):
    if draws<100:raise ValueError('At least 100 bootstrap draws required')
    strata=defaultdict(lambda:defaultdict(list))
    for row in tasks:
        strata[row['skill'] if track=='B' else '*'][row['family_id']].append(row)
    families={row['family_id'] for row in tasks}
    family_skills=defaultdict(set)
    for row in tasks:family_skills[row['family_id']].add(row['skill'])
    if track=='B' and any(len(skills)>1 for skills in family_skills.values()):
        return {'ci95':None,'reason':'family-crosses-skill-strata-unsupported','families':len(families),'seed':seed,'draws':draws}
    if not tasks or any(len(blocks)<2 for blocks in strata.values()):
        return {'ci95':None,'method':'stratified-family-cluster-bootstrap' if track=='B' else 'family-cluster-bootstrap','reason':'insufficient-family-replication-within-stratum','families':len(families),'seed':seed,'draws':draws}
    rng=random.Random(seed);scores=[]
    for _ in range(draws):
        sample=[]
        for blocks in strata.values():
            names=sorted(blocks)
            for name in rng.choices(names,k=len(names)):sample.extend(blocks[name])
        scores.append(point(sample,track))
    scores.sort()
    def quantile(q):
        offset=(len(scores)-1)*q;index=int(offset);fraction=offset-index
        return scores[index]*(1-fraction)+scores[min(index+1,len(scores)-1)]*fraction
    return {'ci95':[quantile(.025),quantile(.975)],'method':'stratified-family-cluster-bootstrap' if track=='B' else 'family-cluster-bootstrap','families':len(families),'seed':seed,'draws':draws,'warning':'few-families-interpret-cautiously' if len(families)<10 else None}
