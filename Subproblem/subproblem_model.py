from gurobipy import *
import time
import numpy as np


def run_model(parameters):

    try:
        m = Model("Heuristic")
        m.setParam('TimeLimit', 60 * 60)

        # ------ SETS -----------------------------------------------------------------------------
        Stations = parameters.stations
        Charging_stations = parameters.charging_stations

        # ------ INDICES --------------------------------------------------------------------------
        b = parameters.depot_index

        # ------ PARAMETERS -----------------------------------------------------------------------
        T = parameters.visits
        Q_BV = parameters.Q_BV
        Q_CV = parameters.Q_CV
        Q_S = parameters.Q_S
        L_BV = parameters.L_BV
        L_CV = parameters.L_CV
        L_FV = parameters.L_FV
        L_CS = parameters.L_CS
        L_FS = parameters.L_FS
        I_OC = parameters.I_OC
        I_IC = parameters.I_IC
        I_IF = parameters.I_IF

        V_B = parameters.V
        V_O = parameters.V_O
        R_O = parameters.R_O

        W_V = parameters.W_V
        W_R = parameters.W_R

        # ------ VARIABLES ------------------------------------------------------------------------
        q_B = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="q_B")
        q_CCU = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="q_CCU")
        q_FCU = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="q_FCU")
        q_CCL = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="q_CCL")
        q_FCL = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="q_FCL")
        l_BV = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="l_BV")
        l_CV = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="l_CV")
        l_FV = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="l_FV")
        v_S_floor = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="v_S_floor")
        v_S_ceiling = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="v_S_ceiling")
        v_C_floor = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="v_C_floor")
        v_C_ceiling = m.addVars({i for i in Stations[1:]}, vtype=GRB.CONTINUOUS, lb=0, name="v_C_ceiling")
        r_F = m.addVar(vtype=GRB.CONTINUOUS, lb=0, name="r_F")

        # ------ CONSTRAINTS -----------------------------------------------------------------------
        # Vehicle Loading Constraints
        m.addConstrs(q_B[i] <= l_BV[i] for i in Stations[1:])
        m.addConstrs(q_CCL[k] + q_FCL[k] <= Q_CV - l_CV[k] - l_FV[k] + q_CCU[k] + q_FCU[k] for k in Stations[1:])
        if b:
            m.addConstr(l_BV[b+1]-Q_BV == 0)
            m.addConstr(q_B[b] == 0)
        for k in Stations[1:-1]:
            if k != b:
                m.addConstr(l_BV[k+1] - l_BV[k] + q_B[k] == 0)
        m.addConstrs(l_CV[k+1] - l_CV[k] + q_CCU[k] - q_CCL[k] == 0 for k in Stations[1:-1])
        m.addConstrs(l_FV[k+1] - l_FV[k] + q_FCU[k] - q_FCL[k] == 0 for k in Stations[1:-1])
        m.addConstr(l_BV[1] == L_BV)
        m.addConstr(l_CV[1] == L_CV)
        m.addConstr(l_FV[1] == L_FV)

        # Station loading constraints
        for k in Stations[1:]:
            if k != b:
                m.addConstr(q_B[k] <= L_FS[k] + q_FCU[k] - q_FCL[k])
                m.addConstr(q_FCL[k] <= L_FS[k])
                m.addConstr(q_CCL[k] <= L_CS[k])
                m.addConstr(q_FCU[k] + q_CCU[k] - q_FCL[k] - q_CCL[k] <= Q_S[k] - L_CS[k] - L_FS[k])

        # Violations
        m.addConstrs(
            L_CS[k] + q_B[k] + q_CCU[k] - q_CCL[k] + I_IC[k] - I_OC[k] + v_S_floor[k] >= 0 for k in Stations[1:])
        m.addConstrs(
            L_CS[k] + q_CCU[k] - q_CCL[k] + L_FS[k] + q_FCU[k] - q_FCL[k] + I_IC[k] + I_IF[k] - I_OC[k] + v_S_floor[k]
            - v_C_floor[k] <= Q_S[k] for k in Stations[1:])
        m.addConstrs(
            L_CS[k] + q_B[k] + q_CCU[k] - q_CCL[k] - I_OC[k] + v_S_ceiling[k] >= 0 for k in Stations[1:])
        m.addConstrs(
            L_CS[k] + q_CCU[k] - q_CCL[k] + L_FS[k] + q_FCU[k] - q_FCL[k] + I_IC[k] + I_IF[k] - v_C_ceiling[k]
            <= Q_S[k] for k in Stations[1:])

        # Reward
        m.addConstr(r_F <= quicksum(q_FCU[k] for k in Charging_stations))

        # ------ OBJECTIVE -----------------------------------------------------------------------
        m.setObjective(W_V * (V_O + quicksum(V_B[k] - 1/2 * (
                v_S_floor[k] + v_S_ceiling[k] + v_C_floor[k] + v_C_ceiling[k]) for k in Stations[1:])) + W_R * (
                R_O + r_F), GRB.MAXIMIZE)

        m.optimize()

        obj_val = m.getObjective().getValue()

        return obj_val

    except GurobiError:
            print(GurobiError.message)
