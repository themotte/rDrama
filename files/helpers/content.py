from typing import Any, TYPE_CHECKING, Optional, Union

from files.helpers.const import PERMS

if TYPE_CHECKING:
	from files.classes import Submission, Comment, User
else:
	Submission = Any
	Comment = Any
	User = Any

def moderated_body(target:Union[Submission, Comment], 
		   v:Optional[User]) -> Optional[str]:
	if v and (v.admin_level >= PERMS['POST_COMMENT_MODERATION'] \
			or v.id == target.author_id):
		return None
	if target.deleted_utc: return 'Deleted by author'
	if target.is_banned or target.filter_state == 'removed': return 'Removed'
	if target.filter_state == 'filtered': return 'Filtered'
	return None
