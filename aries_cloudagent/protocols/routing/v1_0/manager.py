"""Routing manager classes for tracking and inspecting routing records."""

from typing import Sequence

from ....config.injection_context import InjectionContext
from ....core.error import BaseError
from ....storage.error import (
    StorageError,
    StorageDuplicateError,
    StorageNotFoundError,
)

from .messages.route_update_request import RouteUpdateRequest
from .models.route_record import RouteRecord
from .models.route_update import RouteUpdate
from .models.route_updated import RouteUpdated


class RoutingManagerError(BaseError):
    """Generic routing error."""


class RouteNotFoundError(RoutingManagerError):
    """Requested route was not found."""


class RoutingManager:
    """Class for handling routing records."""

    RECORD_TYPE = "forward_route"

    def __init__(self, context: InjectionContext):
        """
        Initialize a RoutingManager.

        Args:
            context: The context for this manager
        """
        self._context = context
        if not context:
            raise RoutingManagerError("Missing request context")

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def get_recipient(self, recip_verkey: str) -> RouteRecord:
        """
        Resolve the recipient for a verkey.

        Args:
            recip_verkey: The verkey ("to") of the incoming Forward message

        Returns:
            The `RouteRecord` associated with this verkey

        """
        if not recip_verkey:
            raise RoutingManagerError("Must pass non-empty recip_verkey")

        try:
            record = await RouteRecord.retrieve_by_recipient_key(
                self.context,
                recip_verkey
            )
        except StorageDuplicateError:
            raise RouteNotFoundError(
                f"More than one route records found with recipient key: {recip_verkey}"
            )
        except StorageNotFoundError:
            raise RouteNotFoundError(
                f"No route found with recipient key: {recip_verkey}"
            )

        return record

    async def get_routes(
        self, client_connection_id: str = None, tag_filter: dict = None
    ) -> Sequence[RouteRecord]:
        """
        Fetch all routes associated with the current connection.

        Args:
            client_connection_id: The ID of the connection record
            tag_filter: An optional dictionary of tag filters

        Returns:
            A sequence of route records found by the query

        """
        # Routing protocol acts only as Server, filter out all client records
        filters = {"role": RouteRecord.ROLE_SERVER}
        if client_connection_id:
            filters["connection_id"] = client_connection_id
        if tag_filter:
            for key in ("recipient_key",):
                if key not in tag_filter:
                    continue
                val = tag_filter[key]
                if isinstance(val, str):
                    filters[key] = val
                elif isinstance(val, list):
                    filters[key] = {"$in": val}
                else:
                    raise RoutingManagerError(
                        "Unsupported tag filter: '{}' = {}".format(key, val)
                    )

        results = await RouteRecord.query(self.context, tag_filter=filters)

        return results

    async def delete_route_record(self, route: RouteRecord):
        """Remove an existing route record."""
        await route.delete_record(self.context)

    async def create_route_record(
        self,
        client_connection_id: str = None,
        recipient_key: str = None,
    ) -> RouteRecord:
        """
        Create and store a new RouteRecord.

        Args:
            client_connection_id: The ID of the connection record
            recipient_key: The recipient verkey of the route

        Returns:
            The new routing record

        """
        if not client_connection_id:
            raise RoutingManagerError("Missing client_connection_id")
        if not recipient_key:
            raise RoutingManagerError("Missing recipient_key")
        route = RouteRecord(
            connection_id=client_connection_id,
            recipient_key=recipient_key,
        )
        await route.save(self.context, reason="Created new route")
        return route

    async def update_routes(
        self, client_connection_id: str, updates: Sequence[RouteUpdate]
    ) -> Sequence[RouteUpdated]:
        """
        Update routes associated with the current connection.

        Args:
            client_connection_id: The ID of the connection record
            updates: The sequence of route updates (create/delete) to perform.

        """
        exist_routes = await self.get_routes(client_connection_id)
        exist = {}
        for route in exist_routes:
            exist[route.recipient_key] = route

        updated = []
        for update in updates:
            result = RouteUpdated(
                recipient_key=update.recipient_key, action=update.action
            )
            recip_key = update.recipient_key
            if not recip_key:
                result.result = RouteUpdated.RESULT_CLIENT_ERROR
            elif update.action == RouteUpdate.ACTION_CREATE:
                if recip_key in exist:
                    result.result = RouteUpdated.RESULT_NO_CHANGE
                else:
                    try:
                        await self.create_route_record(
                            client_connection_id=client_connection_id,
                            recipient_key=recip_key
                        )
                    except RoutingManagerError:
                        result.result = RouteUpdated.RESULT_SERVER_ERROR
                    else:
                        result.result = RouteUpdated.RESULT_SUCCESS
            elif update.action == RouteUpdate.ACTION_DELETE:
                if recip_key in exist:
                    try:
                        await self.delete_route_record(exist[recip_key])
                    except StorageError:
                        result.result = RouteUpdated.RESULT_SERVER_ERROR
                    else:
                        result.result = RouteUpdated.RESULT_SUCCESS
                else:
                    result.result = RouteUpdated.RESULT_NO_CHANGE
            else:
                result.result = RouteUpdated.RESULT_CLIENT_ERROR
            updated.append(result)
        return updated

    async def send_create_route(
        self, router_connection_id: str, recip_key: str, outbound_handler
    ):
        """Create and send a route update request.

        Returns: the current routing state (request or done)

        """
        msg = RouteUpdateRequest(
            updates=[
                RouteUpdate(recipient_key=recip_key, action=RouteUpdate.ACTION_CREATE)
            ]
        )
        await outbound_handler(msg, connection_id=router_connection_id)
