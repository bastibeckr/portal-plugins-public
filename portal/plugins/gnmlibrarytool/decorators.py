import logging
logger = logging.getLogger(__name__)

def has_group(groupname):
    def hasgroup_inner(func):
        def func_wrapper(request):
            from pprint import pprint
            from django.core.exceptions import PermissionDenied

            for g in request.user.groups.all():
                pprint(g)
                logger.debug("user {0} is a member of {1}...".format(request.user.username,g.name))
                if g.name==groupname:
                    return func(request)

            logger.error("User {0} is not a member of the group {1}, so denying access".format(request.user.username,groupname))
            raise PermissionDenied
        return func_wrapper
    return hasgroup_inner