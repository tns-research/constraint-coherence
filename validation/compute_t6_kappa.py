#!/usr/bin/env python3
"""
Compute Cohen's kappa for T6 inter-rater reliability.
Compares automated scorer labels vs. manual human classification.

Usage:
    python3 compute_t6_kappa.py [--file annotations.jsonl]
    
Default file: t6_manual_annotations_n20.jsonl (the expert-validated sample)
"""
import json
import argparse
from collections import Counter

def compute_kappa(pairs, labels=('walk', 'drive', 'ambiguous')):
    n = len(pairs)
    if n == 0:
        return {'error': 'No pairs'}
    
    # Confusion matrix
    matrix = {}
    for al in labels:
        for ml in labels:
            matrix[(al, ml)] = sum(1 for a, m in pairs if a == al and m == ml)
    
    # Observed agreement
    agree = sum(matrix[(l, l)] for l in labels)
    p_o = agree / n
    
    # Expected agreement
    auto_counts = Counter(a for a, m in pairs)
    manual_counts = Counter(m for a, m in pairs)
    p_e = sum((auto_counts.get(l, 0)/n) * (manual_counts.get(l, 0)/n) for l in labels)
    
    kappa = (p_o - p_e) / (1 - p_e) if p_e < 1 else 0
    
    # Binary kappa (walk vs drive only)
    binary = [(a, m) for a, m in pairs if a in ('walk', 'drive') and m in ('walk', 'drive')]
    kappa_binary = None
    if binary:
        nb = len(binary)
        ab = sum(1 for a, m in binary if a == m)
        p_o_b = ab / nb
        aw = sum(1 for a, m in binary if a == 'walk') / nb
        mw = sum(1 for a, m in binary if m == 'walk') / nb
        p_e_b = aw * mw + (1-aw) * (1-mw)
        kappa_binary = (p_o_b - p_e_b) / (1 - p_e_b) if p_e_b < 1 else 0
    
    return {
        'n': n,
        'observed_agreement': agree,
        'p_o': round(p_o, 4),
        'p_e': round(p_e, 4),
        'kappa': round(kappa, 3),
        'kappa_binary': round(kappa_binary, 3) if kappa_binary is not None else None,
        'n_binary': len(binary),
        'confusion_matrix': {f'{al}->{ml}': matrix[(al, ml)] for al in labels for ml in labels}
    }

def main():
    parser = argparse.ArgumentParser(description='Compute T6 Cohen kappa')
    parser.add_argument('--file', default='t6_manual_annotations_n20.jsonl')
    args = parser.parse_args()
    
    pairs = []
    with open(args.file) as f:
        for line in f:
            entry = json.loads(line)
            pairs.append((entry['auto_label'], entry['manual_label']))
    
    result = compute_kappa(pairs)
    print(json.dumps(result, indent=2))
    
    print(f"\nCohen's kappa = {result['kappa']}")
    if result['kappa_binary'] is not None:
        print(f"Binary kappa (walk/drive only, n={result['n_binary']}) = {result['kappa_binary']}")
    
    # Interpretation
    k = result['kappa']
    if k < 0: interp = 'Poor'
    elif k < 0.21: interp = 'Slight'
    elif k < 0.41: interp = 'Fair'
    elif k < 0.61: interp = 'Moderate'
    elif k < 0.81: interp = 'Substantial'
    else: interp = 'Almost perfect'
    print(f"Interpretation: {interp} (Landis & Koch 1977)")

if __name__ == '__main__':
    main()
