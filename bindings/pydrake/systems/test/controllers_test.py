from __future__ import print_function

import math
import numpy as np
import unittest

from pydrake.examples.pendulum import PendulumPlant
from pydrake.systems.analysis import Simulator
from pydrake.math import BarycentricMesh
from pydrake.systems.controllers import (
    DynamicProgrammingOptions, FittedValueIteration,
    LinearProgrammingApproximateDynamicProgramming,
    PeriodicBoundaryCondition
)
from pydrake.systems.primitives import Integrator


class TestControllers(unittest.TestCase):
    def test_fitted_value_iteration_pendulum(self):
        plant = PendulumPlant()
        simulator = Simulator(plant)

        def quadratic_regulator_cost(context):
            x = context.get_continuous_state_vector().CopyToVector()
            x[0] = x[0] - math.pi
            u = plant.EvalVectorInput(context, 0).CopyToVector()
            return x.dot(x) + u.dot(u)

        # Note: intentionally under-sampled to keep the problem small
        qbins = np.linspace(0., 2.*math.pi, 11)
        qdotbins = np.linspace(-10., 10., 11)
        state_grid = [set(qbins), set(qdotbins)]

        input_limit = 2.
        input_mesh = [set(np.linspace(-input_limit, input_limit, 5))]
        timestep = 0.01

        num_callbacks = [0]

        def callback(iteration, mesh, cost_to_go, policy):
            # Drawing is slow, don't draw every frame.
            num_callbacks[0] += 1

        options = DynamicProgrammingOptions()
        options.convergence_tol = 1.
        options.periodic_boundary_conditions = [
            PeriodicBoundaryCondition(0, 0., 2.*math.pi)
        ]
        options.visualization_callback = callback

        policy, cost_to_go = FittedValueIteration(simulator,
                                                  quadratic_regulator_cost,
                                                  state_grid, input_mesh,
                                                  timestep, options)

        self.assertGreater(num_callbacks[0], 0)

    def test_linear_programming_approximate_dynamic_programming(self):
        integrator = Integrator(1)
        simulator = Simulator(integrator)

        # minimum time cost function (1 for all non-zero states).
        def cost_function(context):
            x = context.get_continuous_state_vector().CopyToVector()
            if (math.fabs(x[0]) > 0.1):
                return 1.
            else:
                return 0.

        def cost_to_go_function(state, parameters):
            return parameters[0] * math.fabs(state[0])

        state_samples = np.array([[-4., -3., -2., -1., 0., 1., 2., 3., 4.]])
        input_samples = np.array([[-1., 0., 1.]])

        timestep = 1.0
        options = DynamicProgrammingOptions()
        options.discount_factor = 1.

        J = LinearProgrammingApproximateDynamicProgramming(
            simulator, cost_function, cost_to_go_function, 1,
            state_samples, input_samples, timestep, options)

        self.assertAlmostEqual(J[0], 1., delta=1e-6)


if __name__ == '__main__':
    unittest.main()