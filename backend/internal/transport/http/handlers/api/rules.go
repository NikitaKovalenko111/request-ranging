package api

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
	"strconv"
	"strings"
	"time"
)

type ruleOperand struct {
	Type   string `json:"type"`
	Source string `json:"source,omitempty"`
	Field  string `json:"field,omitempty"`
	Value  any    `json:"value,omitempty"`
}

type ruleExpression struct {
	Left     ruleOperand `json:"left"`
	Operator string      `json:"operator"`
	Right    ruleOperand `json:"right"`
}

type ruleDraft struct {
	Name         string           `json:"name"`
	Description  *string          `json:"description"`
	When         []ruleExpression `json:"when"`
	Requirements []ruleExpression `json:"requirements"`
	Logic        string           `json:"logic"`
	Priority     int              `json:"priority"`
	Active       bool             `json:"active"`
}

type ruleDTO struct {
	ID string `json:"id"`
	ruleDraft
	CreatedAt time.Time `json:"createdAt"`
	UpdatedAt time.Time `json:"updatedAt"`
	Version   int       `json:"version"`
}

func field(source, name, label, dataType string, operators ...string) map[string]any {
	return map[string]any{
		"source": source, "name": name, "label": label, "dataType": dataType,
		"nullable": true, "allowedOperators": operators,
	}
}

func (h *Handler) ruleSchema(response http.ResponseWriter, _ *http.Request) {
	numbers := []string{"EQ", "NE", "GT", "GTE", "LT", "LTE", "BETWEEN"}
	stringsOps := []string{"EQ", "NE", "IN", "NOT_IN", "CONTAINS"}
	writeJSON(response, 200, map[string]any{
		"version": "1",
		"orderFields": []any{
			field("ORDER", "id", "Order ID", "STRING", stringsOps...),
			field("ORDER", "parent_id", "Parent order ID", "STRING", stringsOps...),
			field("ORDER", "user_id", "User ID", "STRING", stringsOps...),
			field("ORDER", "sum", "Order amount", "NUMBER", numbers...),
			field("ORDER", "order_type", "Order type", "STRING", stringsOps...),
			field("ORDER", "subject", "Subject", "STRING", stringsOps...),
			field("ORDER", "vip", "VIP", "BOOLEAN", "EQ", "NE"),
			field("ORDER", "status", "Status", "STRING", stringsOps...),
			field("ORDER", "client_msp", "Client MSP", "STRING", stringsOps...),
			field("ORDER", "executor_msp", "Executor MSP", "STRING", stringsOps...),
		},
		"executorFields": []any{
			field("EXECUTOR", "user_id", "Executor ID", "STRING", stringsOps...),
			field("EXECUTOR", "active", "Active", "BOOLEAN", "EQ", "NE"),
			field("EXECUTOR", "daily_count", "Daily count", "NUMBER", numbers...),
			field("EXECUTOR", "max_daily_limit", "Daily limit", "NUMBER", numbers...),
			field("EXECUTOR", "min_accept_sum", "Minimum amount", "NUMBER", numbers...),
			field("EXECUTOR", "max_accept_sum", "Maximum amount", "NUMBER", numbers...),
			field("EXECUTOR", "client_msp", "Client MSP", "STRING", stringsOps...),
			field("EXECUTOR", "executor_msp", "Executor MSP", "STRING", stringsOps...),
			field("EXECUTOR", "order_type", "Order type", "STRING", stringsOps...),
			field("EXECUTOR", "subject", "Subject", "STRING", stringsOps...),
			field("EXECUTOR", "subjects", "Subjects", "STRING_ARRAY", "CONTAINS", "EQ", "NE"),
			field("EXECUTOR", "vip_allowed", "VIP allowed", "BOOLEAN", "EQ", "NE"),
		},
	})
}

func scanRule(row rowScanner) (ruleDTO, error) {
	var value ruleDTO
	var active bool
	var definition, right []byte
	var legacyOperator, description string
	err := row.Scan(&value.ID, &value.Name, &active, &value.Priority, &definition,
		&legacyOperator, &right, &description, &value.CreatedAt, &value.UpdatedAt)
	if err != nil {
		return value, err
	}
	if err := json.Unmarshal(definition, &value.ruleDraft); err != nil || len(value.Requirements) == 0 {
		var left, legacyRight map[string]any
		_ = json.Unmarshal(definition, &left)
		_ = json.Unmarshal(right, &legacyRight)
		value.ruleDraft = ruleDraft{
			Name: value.Name, Description: &description, Logic: "AND",
			Priority: value.Priority, Active: active,
			Requirements: []ruleExpression{legacyExpression(left, legacyOperator, legacyRight)},
		}
	}
	value.Name = strings.TrimSpace(value.Name)
	value.Active = active
	value.Version = 1
	return value, nil
}

func legacyExpression(left map[string]any, operator string, right map[string]any) ruleExpression {
	return ruleExpression{
		Left:     ruleOperand{Type: "FIELD", Source: strings.ToUpper(fmt.Sprint(left["source"])), Field: fmt.Sprint(left["field"])},
		Operator: apiOperator(operator),
		Right:    ruleOperand{Type: operandType(right), Source: strings.ToUpper(fmt.Sprint(right["source"])), Field: fmt.Sprint(right["field"]), Value: right["value"]},
	}
}

func operandType(value map[string]any) string {
	if strings.EqualFold(fmt.Sprint(value["source"]), "constant") {
		return "CONSTANT"
	}
	return "FIELD"
}

func apiOperator(value string) string {
	switch value {
	case "=":
		return "EQ"
	case "!=":
		return "NE"
	case ">":
		return "GT"
	case ">=":
		return "GTE"
	case "<":
		return "LT"
	case "<=":
		return "LTE"
	case "NOT IN":
		return "NOT_IN"
	default:
		return value
	}
}

func (h *Handler) rules(response http.ResponseWriter, request *http.Request) {
	rows, err := h.db.QueryContext(request.Context(), `
		SELECT id, name, active, priority, left_operand, operator, right_operand,
			failure_reason, created_at, updated_at FROM rules ORDER BY priority, id
	`)
	if err != nil {
		writeError(response, 500, "RULES_QUERY_FAILED", err.Error())
		return
	}
	defer rows.Close()
	values := make([]ruleDTO, 0)
	search := strings.ToLower(request.URL.Query().Get("search"))
	activeFilter := request.URL.Query().Get("active")
	for rows.Next() {
		value, scanErr := scanRule(rows)
		if scanErr != nil {
			writeError(response, 500, "RULES_SCAN_FAILED", scanErr.Error())
			return
		}
		if search != "" && !strings.Contains(strings.ToLower(value.Name), search) {
			continue
		}
		if activeFilter != "" && fmt.Sprint(value.Active) != activeFilter {
			continue
		}
		values = append(values, value)
	}
	limit, offset := pageValues(request, 50)
	total := len(values)
	if offset > total {
		offset = total
	}
	end := offset + limit
	if end > total {
		end = total
	}
	writeJSON(response, 200, page[ruleDTO]{Items: values[offset:end], Pagination: pagination{Limit: limit, Offset: offset, Total: total}})
}

func validateRule(value ruleDraft) error {
	if strings.TrimSpace(value.Name) == "" {
		return fmt.Errorf("name is required")
	}
	if len(value.Requirements) == 0 {
		return fmt.Errorf("at least one requirement is required")
	}
	for _, item := range append(value.When, value.Requirements...) {
		if item.Left.Field == "" || item.Operator == "" {
			return fmt.Errorf("rule expression is incomplete")
		}
	}
	return nil
}

func (h *Handler) createRule(response http.ResponseWriter, request *http.Request) {
	var draft ruleDraft
	if err := decode(request, &draft); err != nil {
		writeError(response, 400, "INVALID_RULE", err.Error())
		return
	}
	if err := validateRule(draft); err != nil {
		writeError(response, 400, "INVALID_RULE", err.Error())
		return
	}
	raw, _ := json.Marshal(draft)
	id := fmt.Sprintf("rule-%d", time.Now().UTC().UnixNano())
	description := ""
	if draft.Description != nil {
		description = *draft.Description
	}
	var created, updated time.Time
	err := h.db.QueryRowContext(request.Context(), `
		INSERT INTO rules (id, name, active, priority, left_operand, operator, right_operand, failure_reason)
		VALUES ($1, $2, $3, $4, $5, '=', '{"source":"constant","value":true}', $6)
		RETURNING created_at, updated_at
	`, id, draft.Name, draft.Active, draft.Priority, raw, description).Scan(&created, &updated)
	if err != nil {
		writeError(response, 500, "RULE_CREATE_FAILED", err.Error())
		return
	}
	if err := h.syncRules(request.Context()); err != nil {
		writeError(response, 500, "RULE_SYNC_FAILED", err.Error())
		return
	}
	writeJSON(response, 201, ruleDTO{ID: id, ruleDraft: draft, CreatedAt: created, UpdatedAt: updated, Version: 1})
}

func (h *Handler) updateRule(response http.ResponseWriter, request *http.Request) {
	var draft ruleDraft
	if err := decode(request, &draft); err != nil {
		writeError(response, 400, "INVALID_RULE", err.Error())
		return
	}
	if err := validateRule(draft); err != nil {
		writeError(response, 400, "INVALID_RULE", err.Error())
		return
	}
	raw, _ := json.Marshal(draft)
	description := ""
	if draft.Description != nil {
		description = *draft.Description
	}
	var created, updated time.Time
	err := h.db.QueryRowContext(request.Context(), `
		UPDATE rules SET name=$2, active=$3, priority=$4, left_operand=$5,
			operator='=', right_operand='{"source":"constant","value":true}',
			failure_reason=$6, updated_at=NOW()
		WHERE id=$1 RETURNING created_at, updated_at
	`, request.PathValue("id"), draft.Name, draft.Active, draft.Priority, raw, description).Scan(&created, &updated)
	if err == sql.ErrNoRows {
		writeError(response, 404, "RULE_NOT_FOUND", "Rule not found")
		return
	}
	if err != nil {
		writeError(response, 500, "RULE_UPDATE_FAILED", err.Error())
		return
	}
	if err := h.syncRules(request.Context()); err != nil {
		writeError(response, 500, "RULE_SYNC_FAILED", err.Error())
		return
	}
	writeJSON(response, 200, ruleDTO{ID: request.PathValue("id"), ruleDraft: draft, CreatedAt: created, UpdatedAt: updated, Version: 1})
}

func (h *Handler) getRule(request *http.Request, id string) (ruleDTO, error) {
	return scanRule(h.db.QueryRowContext(request.Context(), `
		SELECT id, name, active, priority, left_operand, operator, right_operand,
			failure_reason, created_at, updated_at FROM rules WHERE id=$1
	`, id))
}

func (h *Handler) patchRule(response http.ResponseWriter, request *http.Request) {
	var patch struct {
		Active   *bool `json:"active"`
		Priority *int  `json:"priority"`
	}
	if err := decode(request, &patch); err != nil {
		writeError(response, 400, "INVALID_RULE_PATCH", err.Error())
		return
	}
	result, err := h.db.ExecContext(request.Context(), `
		UPDATE rules SET active=COALESCE($2, active), priority=COALESCE($3, priority),
			updated_at=NOW() WHERE id=$1
	`, request.PathValue("id"), patch.Active, patch.Priority)
	if err != nil {
		writeError(response, 500, "RULE_PATCH_FAILED", err.Error())
		return
	}
	if count, _ := result.RowsAffected(); count == 0 {
		writeError(response, 404, "RULE_NOT_FOUND", "Rule not found")
		return
	}
	if err := h.syncRules(request.Context()); err != nil {
		writeError(response, 500, "RULE_SYNC_FAILED", err.Error())
		return
	}
	value, err := h.getRule(request, request.PathValue("id"))
	if err != nil {
		writeError(response, 500, "RULE_QUERY_FAILED", err.Error())
		return
	}
	writeJSON(response, 200, value)
}

func (h *Handler) deleteRule(response http.ResponseWriter, request *http.Request) {
	result, err := h.db.ExecContext(request.Context(), "DELETE FROM rules WHERE id=$1", request.PathValue("id"))
	if err != nil {
		writeError(response, 500, "RULE_DELETE_FAILED", err.Error())
		return
	}
	if count, _ := result.RowsAffected(); count == 0 {
		writeError(response, 404, "RULE_NOT_FOUND", "Rule not found")
		return
	}
	if err := h.syncRules(request.Context()); err != nil {
		writeError(response, 500, "RULE_SYNC_FAILED", err.Error())
		return
	}
	response.WriteHeader(http.StatusNoContent)
}

func (h *Handler) syncRules(ctx context.Context) error {
	rows, err := h.db.QueryContext(ctx, `
		SELECT id, name, active, priority, left_operand, operator, right_operand,
			failure_reason, created_at, updated_at FROM rules WHERE active ORDER BY priority, id
	`)
	if err != nil {
		return err
	}
	defer rows.Close()
	rules := make([]map[string]any, 0)
	for rows.Next() {
		value, scanErr := scanRule(rows)
		if scanErr != nil {
			return scanErr
		}
		rules = append(rules, map[string]any{
			"id": value.ID, "name": value.Name, "description": value.Description,
			"enabled": value.Active, "priority": value.Priority, "version": value.Version,
			"condition": dynamicCondition(value.ID, value.ruleDraft),
		})
	}
	if err := rows.Err(); err != nil {
		return err
	}
	payload, err := json.Marshal(map[string]any{"rules": rules})
	if err != nil {
		return err
	}
	return h.redis.Set(ctx, rulesKey, payload, 0).Err()
}

func dynamicCondition(ruleID string, value ruleDraft) map[string]any {
	requirements := make([]any, 0, len(value.Requirements))
	for index, item := range value.Requirements {
		requirements = append(requirements, dynamicExpression(ruleID, index, item, false))
	}
	var required map[string]any
	if len(requirements) == 1 {
		required = requirements[0].(map[string]any)
	} else {
		required = map[string]any{"logic": "AND", "conditions": requirements}
	}
	if len(value.When) == 0 {
		return required
	}
	conditions := make([]any, 0, len(value.When)+1)
	for index, item := range value.When {
		conditions = append(conditions, dynamicExpression(ruleID+"-when", index, item, true))
	}
	conditions = append(conditions, required)
	return map[string]any{"logic": "OR", "conditions": conditions}
}

func dynamicExpression(prefix string, index int, value ruleExpression, negate bool) map[string]any {
	operator := value.Operator
	if operator == "NE" {
		operator = "NEQ"
	}
	if negate {
		operator = negateOperator(operator)
	}
	result := map[string]any{
		"code":     fmt.Sprintf("%s-%d", prefix, index+1),
		"left":     dynamicOperand(value.Left),
		"operator": operator,
	}
	result["right"] = dynamicOperand(value.Right)
	return result
}

func dynamicOperand(value ruleOperand) map[string]any {
	if value.Type == "CONSTANT" {
		return map[string]any{"source": "constant", "value": value.Value}
	}
	return map[string]any{"source": strings.ToLower(value.Source), "field": value.Field}
}

func negateOperator(value string) string {
	negated := map[string]string{
		"EQ": "NEQ", "NEQ": "EQ", "GT": "LTE", "GTE": "LT",
		"LT": "GTE", "LTE": "GT", "IN": "NOT_IN", "NOT_IN": "IN",
		"CONTAINS": "NOT_CONTAINS",
	}
	if result := negated[value]; result != "" {
		return result
	}
	return "NEQ"
}

func (h *Handler) testRule(response http.ResponseWriter, request *http.Request) {
	var body struct {
		Rule       ruleDraft `json:"rule"`
		OrderID    string    `json:"orderId"`
		ExecutorID string    `json:"executorId"`
	}
	if err := decode(request, &body); err != nil {
		writeError(response, 400, "INVALID_TEST", err.Error())
		return
	}
	orderValues, err := h.testOrder(request, body.OrderID)
	if err != nil {
		writeError(response, 404, "ORDER_NOT_FOUND", err.Error())
		return
	}
	executorValues, err := h.testExecutor(request, body.ExecutorID)
	if err != nil {
		writeError(response, 404, "EXECUTOR_NOT_FOUND", err.Error())
		return
	}
	applicable := true
	for _, item := range body.Rule.When {
		if !evaluateExpression(item, orderValues, executorValues) {
			applicable = false
			break
		}
	}
	passed := true
	comparisons := make([]map[string]any, 0, len(body.Rule.Requirements))
	if applicable {
		for _, item := range body.Rule.Requirements {
			left := resolveOperand(item.Left, orderValues, executorValues)
			right := resolveOperand(item.Right, orderValues, executorValues)
			result := compareValues(left, item.Operator, right)
			if !result {
				passed = false
			}
			comparisons = append(comparisons, map[string]any{
				"leftField": item.Left.Field, "leftValue": left, "operator": item.Operator,
				"rightSource": comparisonRightSource(item.Right), "rightValue": right,
			})
		}
	}
	reason := "All requirements passed"
	if !applicable {
		reason = "Rule does not apply to this order"
	}
	if !passed {
		reason = "One or more requirements failed"
	}
	result := "PASS"
	if !passed {
		result = "FAIL"
	}
	writeJSON(response, 200, map[string]any{"result": result, "reason": reason, "comparisons": comparisons})
}

func comparisonRightSource(value ruleOperand) string {
	if value.Type == "CONSTANT" {
		return "CONSTANT"
	}
	if value.Source == "ORDER" {
		return "ORDER_FIELD"
	}
	return "EXECUTOR_FIELD"
}

func evaluateExpression(value ruleExpression, order, executor map[string]any) bool {
	return compareValues(resolveOperand(value.Left, order, executor), value.Operator, resolveOperand(value.Right, order, executor))
}

func resolveOperand(value ruleOperand, order, executor map[string]any) any {
	if value.Type == "CONSTANT" {
		return value.Value
	}
	if value.Source == "ORDER" {
		return order[value.Field]
	}
	return executor[value.Field]
}

func (h *Handler) testOrder(request *http.Request, id string) (map[string]any, error) {
	var attributes []byte
	var weight float64
	var status string
	err := h.db.QueryRowContext(request.Context(), "SELECT attributes, weight, status FROM orders WHERE id=$1", id).
		Scan(&attributes, &weight, &status)
	if err != nil {
		return nil, err
	}
	values := make(map[string]any)
	_ = json.Unmarshal(attributes, &values)
	values["id"], values["weight"], values["status"] = id, weight, status
	return values, nil
}

func (h *Handler) testExecutor(request *http.Request, id string) (map[string]any, error) {
	var attributes []byte
	var active bool
	var capacity float64
	var daily int
	err := h.db.QueryRowContext(request.Context(), `
		SELECT attributes, active, capacity, processed_today FROM executors WHERE id=$1
	`, id).Scan(&attributes, &active, &capacity, &daily)
	if err != nil {
		return nil, err
	}
	values := make(map[string]any)
	_ = json.Unmarshal(attributes, &values)
	values["user_id"], values["active"], values["capacity"], values["daily_count"] = id, active, capacity, daily
	return values, nil
}

func compareValues(left any, operator string, right any) bool {
	switch operator {
	case "EQ":
		return reflect.DeepEqual(left, right) || fmt.Sprint(left) == fmt.Sprint(right)
	case "NE":
		return !compareValues(left, "EQ", right)
	case "GT", "GTE", "LT", "LTE":
		l, lok := number(left)
		r, rok := number(right)
		if !lok || !rok {
			return false
		}
		switch operator {
		case "GT":
			return l > r
		case "GTE":
			return l >= r
		case "LT":
			return l < r
		default:
			return l <= r
		}
	case "IN", "NOT_IN":
		found := contains(right, left)
		if operator == "NOT_IN" {
			return !found
		}
		return found
	case "CONTAINS":
		return contains(left, right)
	case "BETWEEN":
		items, ok := right.([]any)
		if !ok || len(items) != 2 {
			return false
		}
		return compareValues(left, "GTE", items[0]) && compareValues(left, "LTE", items[1])
	default:
		return false
	}
}

func number(value any) (float64, bool) {
	switch item := value.(type) {
	case float64:
		return item, true
	case int:
		return float64(item), true
	case int64:
		return float64(item), true
	case json.Number:
		result, err := item.Float64()
		return result, err == nil
	case string:
		result, err := strconv.ParseFloat(item, 64)
		return result, err == nil
	default:
		return 0, false
	}
}

func contains(container, expected any) bool {
	if text, ok := container.(string); ok {
		return strings.Contains(text, fmt.Sprint(expected))
	}
	value := reflect.ValueOf(container)
	if value.Kind() != reflect.Slice && value.Kind() != reflect.Array {
		return false
	}
	for index := 0; index < value.Len(); index++ {
		if compareValues(value.Index(index).Interface(), "EQ", expected) {
			return true
		}
	}
	return false
}
