from state.models import NetworkState, WarehouseUpdate, WarehouseState, Order, OrderStatus, Inventory, ExceptionRecord, ExceptionSeverity, ProcurementRequest, ProcurementStatus
from state.repository import NetworkStateRepository
from datetime import datetime
import uuid

class StateManager:
    def __init__(self, repository: NetworkStateRepository):
        self.repository = repository
        self._initialize_demo_data()
        
    def _initialize_demo_data(self):
        state = self.repository.get_state()
        # Seed demo inventory for WH-001
        state.inventory = {
            "prod-001": [Inventory(product_id="prod-001", warehouse_id="WH-001", available=100, reserved=0, inbound=0, outbound=0, reorder_threshold=20, safety_stock=10)],
            "prod-002": [Inventory(product_id="prod-002", warehouse_id="WH-001", available=5, reserved=0, inbound=0, outbound=0, reorder_threshold=20, safety_stock=10)],
        }
        self.repository.save_state(state)

    def get_network_state(self) -> NetworkState:
        return self.repository.get_state()

    def get_warehouse_state(self, warehouse_id: str) -> WarehouseState | None:
        state = self.repository.get_state()
        return state.warehouses.get(warehouse_id)

    def process_warehouse_update(self, update: WarehouseUpdate) -> None:
        state = self.repository.get_state()
        wh_state = WarehouseState(
            status="ACTIVE",
            orders=update.operational_state.orders,
            workers=update.operational_state.workers,
            workers_required=update.predictions.workers_required,
            capacity_utilization=update.operational_state.capacity_utilization,
            risk_score=update.predictions.risk_score,
            predicted_workload=update.predictions.workload
        )
        state.warehouses[update.warehouse_id] = wh_state
        self.repository.save_state(state)
        
    def create_order(self, order_id: str, customer: dict, items: list) -> Order:
        state = self.repository.get_state()
        new_order = Order(
            id=order_id,
            customer_info=customer,
            items=items,
            status=OrderStatus.CREATED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        state.orders[order_id] = new_order
        self.repository.save_state(state)
        return new_order
        
    def check_inventory_and_allocate(self, order_id: str) -> str:
        state = self.repository.get_state()
        order = state.orders.get(order_id)
        if not order:
            return "Order not found"
            
        product_id = order.items[0].get("id") if order.items else "prod-001"
        qty_needed = 1 # Assuming 1 for demo
        
        inventories = state.inventory.get(product_id, [])
        allocated_wh = None
        
        for inv in inventories:
            if inv.available >= qty_needed:
                inv.available -= qty_needed
                inv.reserved += qty_needed
                allocated_wh = inv.warehouse_id
                
                # Check threshold for replenishment
                if inv.available < inv.reorder_threshold:
                    self.create_exception(
                        type="LOW_STOCK",
                        severity=ExceptionSeverity.MEDIUM,
                        source="Head Agent Inventory Check",
                        related_entity=product_id,
                        description=f"Inventory for {product_id} fell below threshold ({inv.available} left).",
                        recommended_action="Initiate procurement request to seller."
                    )
                    self.create_procurement_request(product_id, 50, "SELLER-1")
                break
                
        if allocated_wh:
            order.assigned_fc = allocated_wh
            order.status = OrderStatus.FULFILLMENT_ASSIGNED
        else:
            order.status = OrderStatus.FAILED
            self.create_exception(
                type="STOCKOUT",
                severity=ExceptionSeverity.CRITICAL,
                source="Head Agent Order Routing",
                related_entity=order_id,
                description=f"Could not fulfill order {order_id} due to stockout across network.",
                recommended_action="Route to direct-seller fulfillment or inter-warehouse transfer."
            )
            
        self.repository.save_state(state)
        return allocated_wh
        
    def create_exception(self, type: str, severity: ExceptionSeverity, source: str, related_entity: str, description: str, recommended_action: str):
        state = self.repository.get_state()
        exc_id = str(uuid.uuid4())
        exc = ExceptionRecord(
            id=exc_id, type=type, severity=severity, source=source, 
            timestamp=datetime.utcnow(), related_entity=related_entity, 
            description=description, recommended_action=recommended_action
        )
        state.exceptions[exc_id] = exc
        self.repository.save_state(state)
        
    def create_procurement_request(self, product_id: str, quantity: int, seller_id: str):
        state = self.repository.get_state()
        req_id = str(uuid.uuid4())
        req = ProcurementRequest(
            id=req_id, product_id=product_id, quantity=quantity, seller_id=seller_id, created_at=datetime.utcnow()
        )
        state.procurement_requests[req_id] = req
        self.repository.save_state(state)
