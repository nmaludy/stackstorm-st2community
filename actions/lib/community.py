import os
import codecs

from datetime import datetime
from datetime import timedelta

from github import Github
from jinja2 import Environment

from lib.forum_posts import get_forum_posts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def build_text(logger, token, forum_feed_url, template_path, github_users=None,
               delta=timedelta(days=1, minutes=10)):
    """
    Retrieve the following information for a given time period and return slack
    text to be sent:

    * Github issues and pull requests for the provided users
    * Forum posts
    """
    github_users = github_users or []

    template_path = os.path.join(BASE_DIR, '../../', template_path)
    template_path = os.path.abspath(template_path)

    with codecs.open(template_path, encoding='utf-8') as fp:
        template_data = fp.read()

    template_context = {
        'github': {},
        'forum_posts': []
    }

    # 1. Retrieve Github stats for the provided Github users / organizations
    github = Github(token)

    for user in github_users:
        logger.debug('Retrieving Github issues and prs for user %s' % (user))

        github_user = github.get_user(user)

        # Iterate over all the repos
        # TODO - this is slow, use whitelist / blacklist?
        user_issues = []
        user_prs = []

        for repo in github_user.get_repos():
            result = get_issues_and_prs_for_repo(repo=repo, delta=delta)
            user_issues.extend(result['issues'])
            user_prs.extend(result['prs'])

        # NOTE: Jinja doesn't support referencing dict keys with "-" in them
        username = user.replace('-', '_').lower()
        template_context['github'][username] = {
            'user': user,
            'issues': user_issues,
            'pulls': user_prs
        }

    # 2. Retrieve forum posts from forum.stackstorm.com
    logger.debug('Retrieving forum posts')

    forum_posts = get_forum_posts(feed_url=forum_feed_url, delta=delta)
    template_context['forum_posts'] = forum_posts

    # Add all information to the template context and render the template
    env = Environment(trim_blocks=True, lstrip_blocks=True)
    rendered = env.from_string(template_data).render(template_context)
    return rendered
