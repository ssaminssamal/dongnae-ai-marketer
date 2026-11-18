"""Scene directions without location data or invented selling points."""


def build_scene_prompt(facts, improved=True):
    constraints = ('Preserve the exact product shape, colors, ingredients, packaging and existing lettering. '
        'Fixed camera or minimal slow push-in only. No orbit, rotation or product transformation. '
        'Animate only subtle background light. Do not add objects, people or new text. '
        if improved else 'Use dynamic camera movement and cinematic lighting. ')
    return (constraints + 'Create one realistic vertical advertisement shot from the reference photo. '
        'No generated captions or watermarks. Subject context: ' +
        ' / '.join(str(facts.get(k, '')) for k in ('business', 'product', 'description', 'style')))[:950]
