"""Export completed runner output into a readable, independently reviewable sample report."""
import argparse
import json
from pathlib import Path
from salestranscriptqa.corpus import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir',type=Path)
    args=parser.parse_args()
    root=args.run_dir
    progress=json.loads((root/'progress.json').read_text())
    coverage=json.loads((root/'coverage.json').read_text())
    plan=json.loads((root/'source-plan.json').read_text())
    if progress.get('complete') is not True or coverage.get('published') is not False:
        raise RuntimeError('Expected complete, unpublished generation output')
    selection=json.loads((root/'selected/selection.json').read_text())
    questions=json.loads((root/'selected/questions.json').read_text())
    if len(questions)!=selection['selected_questions']:
        raise RuntimeError('Question count does not match coverage')
    rows=[]
    for i,q in enumerate(questions,1):
        rows.append({'item':i,'status':'accepted','failure':None,'job_id':q['provenance']['job_id'],
                     **{k:q[k] for k in ['question_id','domain','question_class','question','gold_answer','supporting_call_ids']}})
    report={'questions':rows,'seed':plan['seed'],'source_units':len(plan['units']),
            'accepted_questions':len(rows),'estimated_usd':progress['estimated_usd'],'run_root':str(root),
            'scope':plan['scope'],'limitations':'Final deduplicated, coherence-selected output; all automated gates, not human gold. Full rejected candidates are retained in the run directory.'}
    path=Path('reports')/(root.name+'-accepted.json')
    write_json(path,report)
    text=['# Accepted sales questions',f'\n{len(rows)} accepted from {len(plan["units"])} source units. Recorded API estimate: ${progress["estimated_usd"]:.4f}.',
          '\n'+report['limitations']+'\n']
    for q in rows:
        text.extend([f'## {q["item"]}. {q["domain"]} / {q["question_class"]}',
                     f'\n**Q:** {q["question"]}\n\n**A:** {q["gold_answer"]}\n'])
    path.with_suffix('.md').write_text('\n'.join(text))
    print(str(path))


if __name__=='__main__':
    main()
