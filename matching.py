from models import User, Skill, UserSkill, ExchangeRequest
from extensions import db


def calculate_compatibility(current_user, candidate_user):
    """
    Calculates detailed skill exchange compatibility score (0-100%)
    between current_user and candidate_user with transparent metric breakdowns.
    """
    if not current_user or not candidate_user or current_user.id == candidate_user.id:
        return None

    # Retrieve teach & learn skill mappings
    my_teach_skills = {us.skill_id: us for us in current_user.user_skills if us.skill_type == 'teach'}
    my_learn_skills = {us.skill_id: us for us in current_user.user_skills if us.skill_type == 'learn'}
    
    their_teach_skills = {us.skill_id: us for us in candidate_user.user_skills if us.skill_type == 'teach'}
    their_learn_skills = {us.skill_id: us for us in candidate_user.user_skills if us.skill_type == 'learn'}

    # Find overlapping skills
    they_teach_you_ids = set(their_teach_skills.keys()) & set(my_learn_skills.keys())
    you_teach_them_ids = set(my_teach_skills.keys()) & set(their_learn_skills.keys())

    score = 0
    reasons = []
    breakdown = {
        'skill_match_points': 0,
        'skill_match_label': '',
        'multi_skill_bonus': 0,
        'proficiency_bonus': 0,
        'schedule_bonus': 0,
        'location_bonus': 0,
        'reputation_bonus': 0
    }

    # 1. Mutual Skill Swap Check (The gold standard of Smart Swap)
    is_mutual = bool(they_teach_you_ids and you_teach_them_ids)

    if is_mutual:
        score += 55
        breakdown['skill_match_points'] = 55
        breakdown['skill_match_label'] = 'Mutual 2-Way Exchange'
        reasons.append("Perfect mutual exchange: Both users have skills the other wants to learn!")
        
        # Extra points for multi-skill overlap
        extra_pairs = (len(they_teach_you_ids) - 1) + (len(you_teach_them_ids) - 1)
        if extra_pairs > 0:
            bonus = min(extra_pairs * 5, 15)
            score += bonus
            breakdown['multi_skill_bonus'] = bonus
            reasons.append(f"Multiple skill overlaps found (+{bonus}%)")
    elif they_teach_you_ids:
        score += 35
        breakdown['skill_match_points'] = 35
        breakdown['skill_match_label'] = 'Mentor Available (They teach what you want)'
        reasons.append("They teach skills you are actively looking to learn.")
    elif you_teach_them_ids:
        score += 25
        breakdown['skill_match_points'] = 25
        breakdown['skill_match_label'] = 'Learner Interested (You teach what they want)'
        reasons.append("You have skills they want to learn.")
    else:
        # Check category interests
        my_learn_categories = {my_learn_skills[s_id].skill.category for s_id in my_learn_skills if my_learn_skills[s_id].skill}
        their_teach_categories = {their_teach_skills[s_id].skill.category for s_id in their_teach_skills if their_teach_skills[s_id].skill}
        shared_cats = my_learn_categories & their_teach_categories
        if shared_cats:
            score += 15
            breakdown['skill_match_points'] = 15
            breakdown['skill_match_label'] = 'Common Domain Interests'
            reasons.append(f"Shared domain interest in {', '.join(shared_cats)}")
        else:
            return None  # No meaningful match to recommend

    # 2. Proficiency & Mentorship Bonus
    prof_bonus = 0
    for sid in they_teach_you_ids:
        teacher_prof = their_teach_skills[sid].proficiency_level
        if teacher_prof in ['Advanced', 'Expert']:
            prof_bonus = 10
            breakdown['proficiency_bonus'] = 10
            reasons.append(f"High proficiency mentor available for {their_teach_skills[sid].skill.name}")
            break
    score += prof_bonus

    # 3. Availability Compatibility
    my_avail = (current_user.availability or '').lower()
    cand_avail = (candidate_user.availability or '').lower()
    if my_avail and cand_avail:
        if my_avail == cand_avail or 'flexible' in my_avail or 'flexible' in cand_avail:
            score += 10
            breakdown['schedule_bonus'] = 10
            reasons.append(f"Compatible schedules ({candidate_user.availability})")

    # 4. Location / Remote Compatibility
    my_loc = (current_user.location or '').lower()
    cand_loc = (candidate_user.location or '').lower()
    if ('remote' in my_loc and 'remote' in cand_loc) or (my_loc and my_loc == cand_loc):
        score += 10
        breakdown['location_bonus'] = 10
        reasons.append(f"Location match ({candidate_user.location})")
    elif 'remote' in cand_loc or 'remote' in my_loc or 'global' in cand_loc or 'global' in my_loc:
        score += 5
        breakdown['location_bonus'] = 5
        reasons.append("Remote learning friendly")

    # 5. High Rating & Community Trust Bonus
    if candidate_user.average_rating >= 4.5 and candidate_user.rating_count > 0:
        score += 10
        breakdown['reputation_bonus'] = 10
        reasons.append(f"Top-rated user ({candidate_user.average_rating}★ from {candidate_user.rating_count} reviews)")
    elif candidate_user.average_rating >= 4.0:
        score += 5
        breakdown['reputation_bonus'] = 5

    # Cap score at 100%
    score = min(max(score, 10), 100)
    breakdown['total_score'] = score

    # Determine badge and styling
    if score >= 85:
        badge = "Perfect Mutual Match"
        badge_class = "success"
        badge_icon = "bi-stars"
    elif score >= 70:
        badge = "Strong Match"
        badge_class = "primary"
        badge_icon = "bi-lightning-charge-fill"
    elif score >= 50:
        badge = "Good Match"
        badge_class = "info"
        badge_icon = "bi-check-circle-fill"
    else:
        badge = "Skill Match"
        badge_class = "secondary"
        badge_icon = "bi-arrow-left-right"

    they_teach_you = [their_teach_skills[sid].skill for sid in they_teach_you_ids]
    you_teach_them = [my_teach_skills[sid].skill for sid in you_teach_them_ids]

    return {
        'user': candidate_user,
        'score': score,
        'badge': badge,
        'badge_class': badge_class,
        'badge_icon': badge_icon,
        'is_mutual': is_mutual,
        'they_teach_you': they_teach_you,
        'you_teach_them': you_teach_them,
        'all_they_teach': [us.skill for us in candidate_user.user_skills if us.skill_type == 'teach'],
        'all_they_want': [us.skill for us in candidate_user.user_skills if us.skill_type == 'learn'],
        'reasons': reasons,
        'breakdown': breakdown
    }


def get_smart_matches(current_user, limit=20, category=None, min_score=20):
    """
    Returns ranked list of best exchange partners for current_user.
    """
    if not current_user or not current_user.is_authenticated:
        return []

    # Get all active other users
    candidates = User.query.filter(
        User.id != current_user.id,
        User.is_active_account == True
    ).all()

    matches = []
    for candidate in candidates:
        result = calculate_compatibility(current_user, candidate)
        if result and result['score'] >= min_score:
            if category:
                # Filter if candidate teaches or wants any skill in this category
                cand_cats = {us.skill.category for us in candidate.user_skills if us.skill}
                if category not in cand_cats:
                    continue
            matches.append(result)

    # Sort descending by compatibility score, then by candidate rating
    matches.sort(key=lambda m: (m['score'], m['user'].average_rating), reverse=True)
    return matches[:limit]
