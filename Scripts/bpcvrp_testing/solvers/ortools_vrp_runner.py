import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

@dataclass
class SolveResult:
    status: str
    has_solution: bool
    objective: Optional[float]
    solution: Optional[Dict[str, Any]]
    time: float
    raw_result: Any


class ORToolsVRPRunner:
    def solve(self, data: Dict[str, Any], time_limit: Optional[float] = None) -> SolveResult:
        manager = pywrapcp.RoutingIndexManager(
            len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
        )

        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["distance_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        routing.AddDimension(
            transit_callback_index,
            0,
            100000,
            True,
            "Distance"
        )

        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data["demands"][from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            data["vehicle_capacities"],
            True,
            "Capacity"
        )

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        if time_limit is not None:
            search_parameters.time_limit.FromSeconds(int(time_limit))

        start = time.perf_counter()
        solution = routing.SolveWithParameters(search_parameters)
        end = time.perf_counter()

        elapsed = end - start
        has_solution = solution is not None
        objective = solution.ObjectiveValue() if has_solution else None

        solution_dict = {}
        if has_solution:
            routes = []
            for vehicle_id in range(data["num_vehicles"]):
                index = routing.Start(vehicle_id)
                route = []
                while not routing.IsEnd(index):
                    route.append(manager.IndexToNode(index))
                    index = solution.Value(routing.NextVar(index))
                route.append(manager.IndexToNode(index))
                routes.append(route)
            solution_dict["routes"] = routes

        return SolveResult(
            status="SUCCESS" if has_solution else "NO_SOLUTION",
            has_solution=has_solution,
            objective=objective,
            solution=solution_dict if has_solution else None,
            time=elapsed,
            raw_result=solution
        )
    

    def solve_instance(self, instance_obj: Any, time_limit: Optional[float] = None) -> SolveResult:
        return self.solve(instance_obj.to_ortools(), time_limit=time_limit)
