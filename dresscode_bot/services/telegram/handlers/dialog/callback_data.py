from aiogram.filters.callback_data import CallbackData


class PaginationCallbackData(CallbackData, prefix="pagination"):
    page: int = 1


class GroupsCallbackData(PaginationCallbackData, prefix="groups"):
    pass


class GroupCallbackData(CallbackData, prefix="group"):
    group_id: int


class GroupChangeOwnerCallbackData(CallbackData, prefix="group_change_owner"):
    group_id: int


class GroupFunctionsCallbackData(PaginationCallbackData, prefix="group_functions"):
    group_id: int


class GroupManagersCallbackData(PaginationCallbackData, prefix="group_managers"):
    group_id: int


class GroupManagerAddCallbackData(CallbackData, prefix="group_add_manager"):
    group_id: int


class GroupManagerCallbackData(CallbackData, prefix="group_manager"):
    group_id: int
    manager_id: int


class GroupManagerRemoveCallbackData(CallbackData, prefix="group_manager_remove"):
    group_id: int
    manager_id: int
