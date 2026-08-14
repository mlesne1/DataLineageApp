from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


def local_name(tag: str) -> str:
	"""Return XML local tag name (strip namespace if present)."""
	if "}" in tag:
		return tag.split("}", 1)[1]
	return tag


def collect_root_records(root: ET.Element, tag_name: str) -> list[dict[str, str]]:
	"""Collect direct root child records of a given tag into flat dicts."""
	records: list[dict[str, str]] = []
	for child in root:
		if not isinstance(child.tag, str) or local_name(child.tag) != tag_name:
			continue

		record: dict[str, str] = {}
		for field in child:
			if not isinstance(field.tag, str):
				continue
			record[local_name(field.tag)] = field.text.strip() if field.text else ""
		records.append(record)
	return records


def with_nested_properties(
	properties: dict[str, str],
	**nested: object,
) -> dict[str, object]:
	payload: dict[str, object] = dict(properties)
	payload.update(nested)
	return payload


def prune_empty_containers(value: object) -> object:
	"""Recursively remove empty dict/list containers from nested JSON payloads."""
	if isinstance(value, dict):
		cleaned_dict: dict[str, object] = {}
		for key, item in value.items():
			cleaned_item = prune_empty_containers(item)
			if cleaned_item == {} or cleaned_item == []:
				continue
			cleaned_dict[key] = cleaned_item
		return cleaned_dict

	if isinstance(value, list):
		cleaned_list = [prune_empty_containers(item) for item in value]
		return [item for item in cleaned_list if item != {} and item != []]

	return value


@dataclass
class BuildContext:
	projects: list[dict[str, str]] = field(default_factory=list)
	business_units: list[dict[str, str]] = field(default_factory=list)
	data_warehouses: list[dict[str, str]] = field(default_factory=list)
	sql_server_connections: list[dict[str, str]] = field(default_factory=list)
	data_sources: list[dict[str, str]] = field(default_factory=list)
	excel_data_sources: list[dict[str, str]] = field(default_factory=list)
	single_text_file_sources: list[dict[str, str]] = field(default_factory=list)
	data_tables: list[dict[str, str]] = field(default_factory=list)
	data_fields: list[dict[str, str]] = field(default_factory=list)
	markup_objects: list[dict[str, str]] = field(default_factory=list)
	transformations: list[dict[str, str]] = field(default_factory=list)
	lookup_fields: list[dict[str, str]] = field(default_factory=list)
	conditional_lookup_fields: list[dict[str, str]] = field(default_factory=list)
	conditions: list[dict[str, str]] = field(default_factory=list)
	joins: list[dict[str, str]] = field(default_factory=list)
	data_movement_relations: list[dict[str, str]] = field(default_factory=list)
	data_warehouse_mapping_tables: list[dict[str, str]] = field(default_factory=list)
	selection_rules: list[dict[str, str]] = field(default_factory=list)
	selection_rule_fields: list[dict[str, str]] = field(default_factory=list)
	related_records: list[dict[str, str]] = field(default_factory=list)
	related_record_mapping_fields: list[dict[str, str]] = field(default_factory=list)
	related_record_relations: list[dict[str, str]] = field(default_factory=list)
	data_relations: list[dict[str, str]] = field(default_factory=list)
	views: list[dict[str, str]] = field(default_factory=list)
	view_definitions: list[dict[str, str]] = field(default_factory=list)
	business_function_users: list[dict[str, str]] = field(default_factory=list)
	business_function_user_parameters: list[dict[str, str]] = field(default_factory=list)
	business_function_user_values: list[dict[str, str]] = field(default_factory=list)
	table_inserts: list[dict[str, str]] = field(default_factory=list)
	table_insert_mappings: list[dict[str, str]] = field(default_factory=list)
	table_insert_selection_rules: list[dict[str, str]] = field(default_factory=list)
	table_insert_selection_rule_fields: list[dict[str, str]] = field(default_factory=list)

	business_units_by_project: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	warehouses_by_project: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	connections_by_warehouse: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	data_sources_by_business_unit: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	tables_by_connection: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	fields_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	transformations_by_field: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	lookup_fields_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	conditions_by_lookup_field: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	conditions_by_transformation: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	conditions_by_bfu: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	joins_by_lookup_field: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	data_movement_relations_by_destination_field: dict[str, list[dict[str, str]]] = field(
		default_factory=dict
	)
	mapping_tables_by_destination_table: dict[str, list[dict[str, str]]] = field(
		default_factory=dict
	)
	selection_rules_by_mapping_table: dict[str, list[dict[str, str]]] = field(
		default_factory=dict
	)
	selection_rules_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	selection_rule_fields_by_rule: dict[str, list[dict[str, str]]] = field(
		default_factory=dict
	)
	related_records_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	related_record_mapping_fields_by_record: dict[str, list[dict[str, str]]] = field(
		default_factory=dict
	)
	related_record_relations_by_record: dict[str, list[dict[str, str]]] = field(
		default_factory=dict
	)
	relations_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	business_unit_names_by_id: dict[str, str] = field(default_factory=dict)
	excel_data_sources_by_id: dict[str, dict[str, str]] = field(default_factory=dict)
	warehouse_names_by_id: dict[str, str] = field(default_factory=dict)
	connection_warehouse_by_id: dict[str, str] = field(default_factory=dict)
	table_connection_by_id: dict[str, str] = field(default_factory=dict)
	table_warehouse_by_id: dict[str, str] = field(default_factory=dict)
	table_schema_by_id: dict[str, str] = field(default_factory=dict)
	table_names_by_id: dict[str, str] = field(default_factory=dict)
	field_names_by_id: dict[str, str] = field(default_factory=dict)
	field_table_by_id: dict[str, str] = field(default_factory=dict)
	field_aliases_by_id: dict[str, list[str]] = field(default_factory=dict)
	conditional_lookup_field_name_by_id: dict[str, str] = field(default_factory=dict)
	views_by_id: dict[str, dict[str, str]] = field(default_factory=dict)
	view_definitions_by_id: dict[str, dict[str, str]] = field(default_factory=dict)
	view_ids: set[str] = field(default_factory=set)
	business_function_users_by_project: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	business_function_user_parameters_by_user: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	business_function_user_values_by_user: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	table_inserts_by_destination_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	table_insert_mappings_by_insert: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	table_insert_selection_rules_by_insert: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	table_insert_selection_rule_fields_by_rule: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	table_insert_scripts: list[dict[str, str]] = field(default_factory=list)
	table_insert_scripts_by_insert: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	bfus_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	bfu_data_field_by_user: dict[str, str] = field(default_factory=dict)
	custom_hash_field_items: list[dict[str, str]] = field(default_factory=list)
	custom_hash_field_items_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	aggregate_table_fields: list[dict[str, str]] = field(default_factory=list)
	aggregate_table_fields_by_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	data_source_query_tables: list[dict[str, str]] = field(default_factory=list)
	data_source_query_tables_by_source: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_models: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_tables: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_fields: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_relations: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_relation_items: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_selection_rules: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_selection_rule_fields: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_measures: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_measure_custom_scripts: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_models_by_project: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_tables_by_model: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_fields_by_sl_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_relations_by_model: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_relation_items_by_relation: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_selection_rules_by_sl_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_selection_rule_fields_by_rule: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_measures_by_sl_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_measure_custom_scripts_by_measure: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_field_names_by_id: dict[str, str] = field(default_factory=dict)
	odx_connect_datasources: list[dict[str, str]] = field(default_factory=list)
	cdata_data_sources: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_hierarchies: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_hierarchy_fields: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_security_setups: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_security_setup_relations: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_dynamic_security_setup_items: list[dict[str, str]] = field(default_factory=list)
	semantic_layer_hierarchies_by_sl_table: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_hierarchy_fields_by_hierarchy: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_security_setups_by_sl_field: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_security_setup_relations_by_setup: dict[str, list[dict[str, str]]] = field(default_factory=dict)
	semantic_layer_dynamic_security_setup_items_by_setup: dict[str, list[dict[str, str]]] = field(default_factory=dict)


class NestedJsonBuilder:
	def __init__(self, root: ET.Element):
		self.root = root
		self.ctx = BuildContext()

	def build(self) -> dict[str, dict[str, object]]:
		self.collect_projects()
		self.collect_business_units()
		self.collect_data_warehouses()
		self.collect_sql_server_connections()
		self.collect_data_sources()
		self.collect_excel_data_sources()
		self.collect_single_text_file_sources()
		self.collect_data_tables()
		self.collect_data_fields()
		self.collect_markup_objects()
		self.collect_transformations()
		self.collect_lookup_fields()
		self.collect_conditional_lookup_fields()
		self.collect_conditions()
		self.collect_joins()
		self.collect_data_movement_relations()
		self.collect_data_warehouse_mapping_tables()
		self.collect_selection_rules()
		self.collect_selection_rule_fields()
		self.collect_related_records()
		self.collect_related_record_mapping_fields()
		self.collect_related_record_relations()
		self.collect_data_relations()
		self.collect_views()
		self.collect_view_definitions()
		self.collect_business_function_users()
		self.collect_business_function_user_parameters()
		self.collect_business_function_user_values()
		self.collect_table_inserts()
		self.collect_table_insert_mappings()
		self.collect_table_insert_selection_rules()
		self.collect_table_insert_selection_rule_fields()
		self.collect_custom_hash_field_items()
		self.collect_aggregate_table_fields()
		self.collect_data_source_query_tables()
		self.collect_table_insert_scripts()
		self.collect_semantic_layer_models()
		self.collect_semantic_layer_tables()
		self.collect_semantic_layer_fields()
		self.collect_semantic_layer_relations()
		self.collect_semantic_layer_relation_items()
		self.collect_semantic_layer_selection_rules()
		self.collect_semantic_layer_selection_rule_fields()
		self.collect_semantic_layer_measures()
		self.collect_semantic_layer_measure_custom_scripts()
		self.collect_odx_connect_datasources()
		self.collect_cdata_data_sources()
		self.collect_semantic_layer_hierarchies()
		self.collect_semantic_layer_hierarchy_fields()
		self.collect_semantic_layer_security_setups()
		self.collect_semantic_layer_security_setup_relations()
		self.collect_semantic_layer_dynamic_security_setup_items()

		self.index_business_units()
		self.index_data_warehouses()
		self.index_sql_server_connections()
		self.index_data_sources()
		self.index_excel_data_sources()
		self.index_data_tables()
		self.index_data_fields()
		self.index_field_aliases_from_markup_objects()
		self.index_transformations()
		self.index_lookup_fields()
		self.index_conditional_lookup_fields()
		self.index_conditions()
		self.index_joins()
		self.index_data_movement_relations()
		self.index_data_warehouse_mapping_tables()
		self.index_selection_rules()
		self.index_selection_rule_fields()
		self.index_related_records()
		self.index_related_record_mapping_fields()
		self.index_related_record_relations()
		self.index_data_relations()
		self.index_views()
		self.index_view_definitions()
		self.index_business_function_users()
		self.index_business_function_user_parameters()
		self.index_business_function_user_values()
		self.index_table_inserts()
		self.index_table_insert_mappings()
		self.index_table_insert_selection_rules()
		self.index_table_insert_selection_rule_fields()
		self.index_business_function_users_by_table()
		self.index_custom_hash_field_items()
		self.index_aggregate_table_fields()
		self.index_data_source_query_tables()
		self.index_table_insert_scripts()
		self.index_semantic_layer_models()
		self.index_semantic_layer_tables()
		self.index_semantic_layer_fields()
		self.index_semantic_layer_relations()
		self.index_semantic_layer_relation_items()
		self.index_semantic_layer_selection_rules()
		self.index_semantic_layer_selection_rule_fields()
		self.index_semantic_layer_measures()
		self.index_semantic_layer_measure_custom_scripts()
		self.index_odx_connect_datasources()
		self.index_semantic_layer_hierarchies()
		self.index_semantic_layer_hierarchy_fields()
		self.index_semantic_layer_security_setups()
		self.index_semantic_layer_security_setup_relations()
		self.index_semantic_layer_dynamic_security_setup_items()

		return prune_empty_containers(self.build_projects_payload())

	def collect_projects(self) -> None:
		self.ctx.projects = collect_root_records(self.root, "Projects")

	def collect_business_units(self) -> None:
		self.ctx.business_units = collect_root_records(self.root, "BusinessUnits")

	def collect_data_warehouses(self) -> None:
		self.ctx.data_warehouses = collect_root_records(self.root, "DataWarehouses")

	def collect_sql_server_connections(self) -> None:
		self.ctx.sql_server_connections = collect_root_records(
			self.root,
			"SqlServerConnections",
		)

	def collect_data_sources(self) -> None:
		self.ctx.data_sources = collect_root_records(self.root, "DataSources")

	def collect_excel_data_sources(self) -> None:
		self.ctx.excel_data_sources = collect_root_records(self.root, "ExcelDataSources")

	def collect_single_text_file_sources(self) -> None:
		self.ctx.single_text_file_sources = collect_root_records(
			self.root,
			"SingleTextFileSources",
		)

	def collect_data_tables(self) -> None:
		self.ctx.data_tables = collect_root_records(self.root, "DataTables")

	def collect_data_fields(self) -> None:
		self.ctx.data_fields = collect_root_records(self.root, "DataFields")

	def collect_markup_objects(self) -> None:
		self.ctx.markup_objects = collect_root_records(self.root, "MarkupObjects")

	def collect_transformations(self) -> None:
		self.ctx.transformations = collect_root_records(self.root, "Transformations")

	def collect_lookup_fields(self) -> None:
		self.ctx.lookup_fields = collect_root_records(self.root, "LookupFields")

	def collect_conditional_lookup_fields(self) -> None:
		self.ctx.conditional_lookup_fields = collect_root_records(
			self.root,
			"ConditionalLookupFields",
		)

	def collect_conditions(self) -> None:
		self.ctx.conditions = collect_root_records(self.root, "Conditions")

	def collect_joins(self) -> None:
		self.ctx.joins = collect_root_records(self.root, "Joins")

	def collect_data_movement_relations(self) -> None:
		self.ctx.data_movement_relations = collect_root_records(
			self.root,
			"DataMovementRelations",
		)

	def collect_data_warehouse_mapping_tables(self) -> None:
		self.ctx.data_warehouse_mapping_tables = collect_root_records(
			self.root,
			"DataWarehouseMappingTables",
		)

	def collect_selection_rules(self) -> None:
		self.ctx.selection_rules = collect_root_records(self.root, "SelectionRules")

	def collect_selection_rule_fields(self) -> None:
		self.ctx.selection_rule_fields = collect_root_records(self.root, "SelectionRuleFields")

	def collect_related_records(self) -> None:
		self.ctx.related_records = collect_root_records(self.root, "RelatedRecords")

	def collect_related_record_mapping_fields(self) -> None:
		self.ctx.related_record_mapping_fields = collect_root_records(
			self.root,
			"RelatedRecordMappingFields",
		)

	def collect_related_record_relations(self) -> None:
		self.ctx.related_record_relations = collect_root_records(
			self.root,
			"RelatedRecordRelations",
		)

	def collect_data_relations(self) -> None:
		self.ctx.data_relations = collect_root_records(self.root, "DataRelations")

	def collect_views(self) -> None:
		self.ctx.views = collect_root_records(self.root, "Views")

	def collect_view_definitions(self) -> None:
		self.ctx.view_definitions = collect_root_records(self.root, "ViewDefinitions")

	def collect_business_function_users(self) -> None:
		self.ctx.business_function_users = collect_root_records(self.root, "BusinessFunctionUsers")

	def collect_business_function_user_parameters(self) -> None:
		self.ctx.business_function_user_parameters = collect_root_records(
			self.root, "BusinessFunctionUserParameters"
		)

	def collect_business_function_user_values(self) -> None:
		self.ctx.business_function_user_values = collect_root_records(
			self.root, "BusinessFunctionUserValues"
		)

	def collect_table_inserts(self) -> None:
		self.ctx.table_inserts = collect_root_records(self.root, "TableInserts")

	def collect_table_insert_mappings(self) -> None:
		self.ctx.table_insert_mappings = collect_root_records(self.root, "TableInsertMappings")

	def collect_table_insert_selection_rules(self) -> None:
		self.ctx.table_insert_selection_rules = collect_root_records(
			self.root, "TableInsertSelectionRules"
		)

	def collect_table_insert_selection_rule_fields(self) -> None:
		self.ctx.table_insert_selection_rule_fields = collect_root_records(
			self.root, "TableInsertSelectionRuleFields"
		)

	def collect_custom_hash_field_items(self) -> None:
		self.ctx.custom_hash_field_items = collect_root_records(self.root, "CustomHashFieldItems")

	def collect_aggregate_table_fields(self) -> None:
		self.ctx.aggregate_table_fields = collect_root_records(self.root, "AggregateTableFields")

	def collect_data_source_query_tables(self) -> None:
		self.ctx.data_source_query_tables = collect_root_records(self.root, "DataSourceQueryTables")

	def collect_table_insert_scripts(self) -> None:
		self.ctx.table_insert_scripts = collect_root_records(self.root, "TableInsertScripts")

	def collect_semantic_layer_models(self) -> None:
		self.ctx.semantic_layer_models = collect_root_records(self.root, "SemanticLayerModels")

	def collect_semantic_layer_tables(self) -> None:
		self.ctx.semantic_layer_tables = collect_root_records(self.root, "SemanticLayerTables")

	def collect_semantic_layer_fields(self) -> None:
		self.ctx.semantic_layer_fields = collect_root_records(self.root, "SemanticLayerFields")

	def collect_semantic_layer_relations(self) -> None:
		self.ctx.semantic_layer_relations = collect_root_records(self.root, "SemanticLayerRelations")

	def collect_semantic_layer_relation_items(self) -> None:
		self.ctx.semantic_layer_relation_items = collect_root_records(self.root, "SemanticLayerRelationItems")

	def collect_semantic_layer_selection_rules(self) -> None:
		self.ctx.semantic_layer_selection_rules = collect_root_records(self.root, "SemanticLayerSelectionRules")

	def collect_semantic_layer_selection_rule_fields(self) -> None:
		self.ctx.semantic_layer_selection_rule_fields = collect_root_records(self.root, "SemanticLayerSelectionRuleFields")

	def collect_semantic_layer_measures(self) -> None:
		self.ctx.semantic_layer_measures = collect_root_records(self.root, "SemanticLayerMeasures")

	def collect_semantic_layer_measure_custom_scripts(self) -> None:
		self.ctx.semantic_layer_measure_custom_scripts = collect_root_records(self.root, "SemanticLayerMeasureCustomScripts")

	def collect_odx_connect_datasources(self) -> None:
		self.ctx.odx_connect_datasources = collect_root_records(self.root, "ODXConnectDatasources")

	def collect_cdata_data_sources(self) -> None:
		self.ctx.cdata_data_sources = collect_root_records(self.root, "CDataDataSources")

	def collect_semantic_layer_hierarchies(self) -> None:
		self.ctx.semantic_layer_hierarchies = collect_root_records(self.root, "SemanticLayerHierarchies")

	def collect_semantic_layer_hierarchy_fields(self) -> None:
		self.ctx.semantic_layer_hierarchy_fields = collect_root_records(self.root, "SemanticLayerHierarchyFields")

	def collect_semantic_layer_security_setups(self) -> None:
		self.ctx.semantic_layer_security_setups = collect_root_records(self.root, "SemanticLayerSecuritySetups")

	def collect_semantic_layer_security_setup_relations(self) -> None:
		self.ctx.semantic_layer_security_setup_relations = collect_root_records(self.root, "SemanticLayerSecuritySetupRelations")

	def collect_semantic_layer_dynamic_security_setup_items(self) -> None:
		self.ctx.semantic_layer_dynamic_security_setup_items = collect_root_records(self.root, "SemanticLayerDynamicSecuritySetupItems")

	def index_data_warehouses(self) -> None:
		self.ctx.warehouses_by_project = self._group_by_key(
			self.ctx.data_warehouses,
			"ProjectId",
		)
		for warehouse in self.ctx.data_warehouses:
			warehouse_id = warehouse.get("DataWarehouseId", "")
			warehouse_name = warehouse.get("Name") or warehouse_id or "Unnamed Warehouse"
			if warehouse_id:
				self.ctx.warehouse_names_by_id[warehouse_id] = warehouse_name

	def index_business_units(self) -> None:
		self.ctx.business_units_by_project = self._group_by_key(
			self.ctx.business_units,
			"ProjectId",
		)
		for business_unit in self.ctx.business_units:
			business_unit_id = business_unit.get("BusinessUnitId", "")
			business_unit_name = (
				business_unit.get("Name")
				or business_unit_id
				or "Unnamed Business Unit"
			)
			if business_unit_id:
				self.ctx.business_unit_names_by_id[business_unit_id] = business_unit_name

	def index_sql_server_connections(self) -> None:
		self.ctx.connections_by_warehouse = self._group_by_key(
			self.ctx.sql_server_connections,
			"DataWarehouseId",
		)
		for connection in self.ctx.sql_server_connections:
			connection_id = connection.get("SqlServerConnectionId", "")
			warehouse_id = connection.get("DataWarehouseId", "")
			if connection_id and warehouse_id:
				self.ctx.connection_warehouse_by_id[connection_id] = warehouse_id

	def index_data_sources(self) -> None:
		self.ctx.data_sources_by_business_unit = self._group_by_key(
			self.ctx.data_sources,
			"BusinessUnitId",
		)

	def index_excel_data_sources(self) -> None:
		self.ctx.excel_data_sources_by_id = self._build_lookup_by_id(
			self.ctx.excel_data_sources,
			"ExcelDataSourceId",
		)

	def index_data_tables(self) -> None:
		for table in self.ctx.data_tables:
			table_id = table.get("DataTableId", "")
			table_name = table.get("Name") or table_id or "Unnamed Table"
			table_schema = table.get("SchemaName", "")
			if table_id:
				self.ctx.table_names_by_id[table_id] = table_name
				self.ctx.table_schema_by_id[table_id] = table_schema

			connection_id = table.get("SqlServerConnectionId", "")
			if table_id and connection_id:
				self.ctx.table_connection_by_id[table_id] = connection_id
				warehouse_id = self.ctx.connection_warehouse_by_id.get(connection_id, "")
				if warehouse_id:
					self.ctx.table_warehouse_by_id[table_id] = warehouse_id
			if connection_id:
				self.ctx.tables_by_connection.setdefault(connection_id, []).append(table)

	def index_data_fields(self) -> None:
		self.ctx.fields_by_table = self._group_by_key(self.ctx.data_fields, "DataTableId")
		for field in self.ctx.data_fields:
			field_id = field.get("DataFieldId", "")
			field_name = field.get("Name") or field_id or "Unnamed Field"
			table_id = field.get("DataTableId", "")
			if field_id:
				self.ctx.field_names_by_id[field_id] = field_name
				self.ctx.field_table_by_id[field_id] = table_id

	def index_field_aliases_from_markup_objects(self) -> None:
		for markup_object in self.ctx.markup_objects:
			field_id = markup_object.get("TXObjectId", "")
			if not field_id:
				continue

			field_name = self.ctx.field_names_by_id.get(field_id, "")
			if not field_name:
				continue

			parameter_name = markup_object.get("ParameterName", "")
			if not parameter_name:
				continue

			alias = parameter_name.strip()
			if alias.startswith("[") and alias.endswith("]") and len(alias) >= 2:
				alias = alias[1:-1]

			if not alias or alias == field_name:
				continue

			aliases = self.ctx.field_aliases_by_id.setdefault(field_id, [])
			if alias not in aliases:
				aliases.append(alias)

	def index_transformations(self) -> None:
		self.ctx.transformations_by_field = self._group_by_key(
			self.ctx.transformations,
			"DataFieldId",
		)

	def index_lookup_fields(self) -> None:
		for lookup_field in self.ctx.lookup_fields:
			field_id = lookup_field.get("LookupDataFieldId", "")
			table_id = self.ctx.field_table_by_id.get(field_id, "")
			if table_id:
				self.ctx.lookup_fields_by_table.setdefault(table_id, []).append(lookup_field)

	def index_conditional_lookup_fields(self) -> None:
		for conditional_lookup_field in self.ctx.conditional_lookup_fields:
			conditional_id = conditional_lookup_field.get("ConditionalLookupFieldId", "")
			if not conditional_id:
				continue

			name = (
				self.ctx.field_names_by_id.get(conditional_id)
				or
				conditional_lookup_field.get("Name")
				or conditional_lookup_field.get("ConditionalLookupFieldName")
				or conditional_id
			)
			self.ctx.conditional_lookup_field_name_by_id[conditional_id] = name

		# Fallback from LookupFields when ConditionalLookupFields has no explicit name.
		for lookup_field in self.ctx.lookup_fields:
			conditional_id = lookup_field.get("ConditionalLookupFieldId", "")
			if not conditional_id:
				continue
			if conditional_id in self.ctx.conditional_lookup_field_name_by_id:
				continue

			lookup_name = lookup_field.get("Name") or lookup_field.get("LookupFieldId", "")
			if lookup_name:
				self.ctx.conditional_lookup_field_name_by_id[conditional_id] = lookup_name

	def index_conditions(self) -> None:
		for condition in self.ctx.conditions:
			lookup_field_id = condition.get("LookupFieldId", "")
			if lookup_field_id:
				self.ctx.conditions_by_lookup_field.setdefault(lookup_field_id, []).append(
					condition
				)

			transformation_id = condition.get("TransformationId", "")
			if transformation_id:
				self.ctx.conditions_by_transformation.setdefault(transformation_id, []).append(
					condition
				)

			bfu_id = condition.get("SqlSnippetId", "")
			if bfu_id:
				self.ctx.conditions_by_bfu.setdefault(bfu_id, []).append(condition)

	def index_joins(self) -> None:
		for join in self.ctx.joins:
			lookup_field_id = join.get("LookUpFieldId", "")
			if lookup_field_id:
				self.ctx.joins_by_lookup_field.setdefault(lookup_field_id, []).append(join)

	def index_data_movement_relations(self) -> None:
		self.ctx.data_movement_relations_by_destination_field = self._group_by_key(
			self.ctx.data_movement_relations,
			"DestinationDataFieldId",
		)

	def index_data_warehouse_mapping_tables(self) -> None:
		self.ctx.mapping_tables_by_destination_table = self._group_by_key(
			self.ctx.data_warehouse_mapping_tables,
			"DestinationTableId",
		)

	def index_selection_rules(self) -> None:
		for rule in self.ctx.selection_rules:
			mapping_table_id = rule.get("DataWarehouseMappingTableId", "")
			if mapping_table_id:
				self.ctx.selection_rules_by_mapping_table.setdefault(mapping_table_id, []).append(rule)
			else:
				table_id = rule.get("DataTableId", "")
				if table_id:
					self.ctx.selection_rules_by_table.setdefault(table_id, []).append(rule)

	def index_selection_rule_fields(self) -> None:
		self.ctx.selection_rule_fields_by_rule = self._group_by_key(
			self.ctx.selection_rule_fields,
			"SelectionRuleId",
		)

	def index_related_records(self) -> None:
		self.ctx.related_records_by_table = self._group_by_key(
			self.ctx.related_records,
			"DataManTableId",
		)

	def index_related_record_mapping_fields(self) -> None:
		self.ctx.related_record_mapping_fields_by_record = self._group_by_key(
			self.ctx.related_record_mapping_fields,
			"RelatedRecordId",
		)

	def index_related_record_relations(self) -> None:
		self.ctx.related_record_relations_by_record = self._group_by_key(
			self.ctx.related_record_relations,
			"RelatedRecordId",
		)

	def index_data_relations(self) -> None:
		for relation in self.ctx.data_relations:
			primary_table_id = relation.get("PrimaryDataTableId", "")
			secondary_table_id = relation.get("SecondaryDataTableId", "")

			if primary_table_id:
				self.ctx.relations_by_table.setdefault(primary_table_id, []).append(relation)
			if secondary_table_id and secondary_table_id != primary_table_id:
				self.ctx.relations_by_table.setdefault(secondary_table_id, []).append(
					relation
				)

	def index_views(self) -> None:
		self.ctx.views_by_id = self._build_lookup_by_id(self.ctx.views, "ViewId")
		self.ctx.view_ids = set(self.ctx.views_by_id.keys())

	def index_view_definitions(self) -> None:
		self.ctx.view_definitions_by_id = self._build_lookup_by_id(
			self.ctx.view_definitions,
			"ViewDefinitionId",
		)

	def index_business_function_users(self) -> None:
		self.ctx.business_function_users_by_project = self._group_by_key(
			self.ctx.business_function_users, "ProjectId"
		)

	def index_business_function_user_parameters(self) -> None:
		self.ctx.business_function_user_parameters_by_user = self._group_by_key(
			self.ctx.business_function_user_parameters, "BusinessFunctionUserId"
		)

	def index_business_function_user_values(self) -> None:
		self.ctx.business_function_user_values_by_user = self._group_by_key(
			self.ctx.business_function_user_values, "BusinessFunctionUserId"
		)

	def index_table_inserts(self) -> None:
		self.ctx.table_inserts_by_destination_table = self._group_by_key(
			self.ctx.table_inserts, "DestinationTableId"
		)

	def index_table_insert_mappings(self) -> None:
		self.ctx.table_insert_mappings_by_insert = self._group_by_key(
			self.ctx.table_insert_mappings, "TableInsertId"
		)

	def index_table_insert_selection_rules(self) -> None:
		self.ctx.table_insert_selection_rules_by_insert = self._group_by_key(
			self.ctx.table_insert_selection_rules, "TableInsertId"
		)

	def index_table_insert_selection_rule_fields(self) -> None:
		self.ctx.table_insert_selection_rule_fields_by_rule = self._group_by_key(
			self.ctx.table_insert_selection_rule_fields, "TableInsertSelectionRuleId"
		)

	def index_custom_hash_field_items(self) -> None:
		for item in self.ctx.custom_hash_field_items:
			host_field_id = item.get("CustomHasFieldId", "")
			if not host_field_id:
				continue
			table_id = self.ctx.field_table_by_id.get(host_field_id, "")
			if table_id:
				self.ctx.custom_hash_field_items_by_table.setdefault(table_id, []).append(item)

	def index_aggregate_table_fields(self) -> None:
		for item in self.ctx.aggregate_table_fields:
			host_field_id = item.get("DataFieldId", "")
			if not host_field_id:
				continue
			table_id = self.ctx.field_table_by_id.get(host_field_id, "")
			if table_id:
				self.ctx.aggregate_table_fields_by_table.setdefault(table_id, []).append(item)

	def index_data_source_query_tables(self) -> None:
		for item in self.ctx.data_source_query_tables:
			source_id = item.get("DataSourceId", "")
			if source_id:
				self.ctx.data_source_query_tables_by_source.setdefault(source_id, []).append(item)

	def index_table_insert_scripts(self) -> None:
		self.ctx.table_insert_scripts_by_insert = self._group_by_key(
			self.ctx.table_insert_scripts, "TableInsertId"
		)

	def index_semantic_layer_models(self) -> None:
		self.ctx.semantic_layer_models_by_project = self._group_by_key(
			self.ctx.semantic_layer_models, "ProjectId"
		)

	def index_semantic_layer_tables(self) -> None:
		self.ctx.semantic_layer_tables_by_model = self._group_by_key(
			self.ctx.semantic_layer_tables, "SemanticLayerModelId"
		)

	def index_semantic_layer_fields(self) -> None:
		self.ctx.semantic_layer_fields_by_sl_table = self._group_by_key(
			self.ctx.semantic_layer_fields, "SemanticLayerTableId"
		)
		for sl_field in self.ctx.semantic_layer_fields:
			sl_field_id = sl_field.get("SemanticLayerFieldId", "")
			sl_field_name = sl_field.get("Name") or sl_field_id
			if sl_field_id:
				self.ctx.semantic_layer_field_names_by_id[sl_field_id] = sl_field_name

	def index_semantic_layer_relations(self) -> None:
		self.ctx.semantic_layer_relations_by_model = self._group_by_key(
			self.ctx.semantic_layer_relations, "SemanticLayerModelId"
		)

	def index_semantic_layer_relation_items(self) -> None:
		self.ctx.semantic_layer_relation_items_by_relation = self._group_by_key(
			self.ctx.semantic_layer_relation_items, "SemanticLayerRelationId"
		)

	def index_semantic_layer_selection_rules(self) -> None:
		self.ctx.semantic_layer_selection_rules_by_sl_table = self._group_by_key(
			self.ctx.semantic_layer_selection_rules, "SemanticLayerTableId"
		)

	def index_semantic_layer_selection_rule_fields(self) -> None:
		self.ctx.semantic_layer_selection_rule_fields_by_rule = self._group_by_key(
			self.ctx.semantic_layer_selection_rule_fields, "SemanticLayerSelectionRuleId"
		)

	def index_semantic_layer_measures(self) -> None:
		self.ctx.semantic_layer_measures_by_sl_table = self._group_by_key(
			self.ctx.semantic_layer_measures, "SemanticLayerTableId"
		)

	def index_semantic_layer_measure_custom_scripts(self) -> None:
		self.ctx.semantic_layer_measure_custom_scripts_by_measure = self._group_by_key(
			self.ctx.semantic_layer_measure_custom_scripts, "SemanticLayerMeasureId"
		)

	def index_odx_connect_datasources(self) -> None:
		# ODXConnectDatasources are flat; no grouping needed for sources payload
		pass

	def index_semantic_layer_hierarchies(self) -> None:
		self.ctx.semantic_layer_hierarchies_by_sl_table = self._group_by_key(
			self.ctx.semantic_layer_hierarchies, "SemanticLayerTableId"
		)

	def index_semantic_layer_hierarchy_fields(self) -> None:
		self.ctx.semantic_layer_hierarchy_fields_by_hierarchy = self._group_by_key(
			self.ctx.semantic_layer_hierarchy_fields, "SemanticLayerHierarchyId"
		)

	def index_semantic_layer_security_setups(self) -> None:
		self.ctx.semantic_layer_security_setups_by_sl_field = self._group_by_key(
			self.ctx.semantic_layer_security_setups, "SemanticLayerFieldId"
		)

	def index_semantic_layer_security_setup_relations(self) -> None:
		self.ctx.semantic_layer_security_setup_relations_by_setup = self._group_by_key(
			self.ctx.semantic_layer_security_setup_relations, "SemanticLayerSecuritySetupId"
		)

	def index_semantic_layer_dynamic_security_setup_items(self) -> None:
		self.ctx.semantic_layer_dynamic_security_setup_items_by_setup = self._group_by_key(
			self.ctx.semantic_layer_dynamic_security_setup_items, "SemanticLayerSecuritySetupId"
		)

	def index_business_function_users_by_table(self) -> None:
		# Use BusinessFunctionUserValues with Type=="DataField" to find which field each BFU targets
		bfus_by_id = self._build_lookup_by_id(
			self.ctx.business_function_users, "BusinessFunctionUserId"
		)
		for bfu_value in self.ctx.business_function_user_values:
			if bfu_value.get("Type", "") != "DataField":
				continue
			bfu_id = bfu_value.get("BusinessFunctionUserId", "")
			field_id = bfu_value.get("Value", "")
			if not bfu_id or not field_id or bfu_id in self.ctx.bfu_data_field_by_user:
				continue
			self.ctx.bfu_data_field_by_user[bfu_id] = field_id
			table_id = self.ctx.field_table_by_id.get(field_id, "")
			if table_id and bfu_id in bfus_by_id:
				self.ctx.bfus_by_table.setdefault(table_id, []).append(bfus_by_id[bfu_id])

	def build_projects_payload(self) -> dict[str, dict[str, object]]:
		result: dict[str, dict[str, object]] = {"Projects": {}}

		for project in self.ctx.projects:
			project_name = project.get("Name") or project.get("ProjectId") or "Unnamed Project"
			project_payload = with_nested_properties(
				project,
				DataWarehouses=self.build_warehouses_payload(project),
				SemanticLayerModels=self.build_semantic_layer_models_payload(project),
				Sources=self.build_sources_payload(project),
				BusinessFunctionUsers=self.build_business_function_users_payload(project),
			)
			result["Projects"][project_name] = project_payload

		return result

	def build_sources_payload(self, project: dict[str, str]) -> dict[str, dict[str, dict[str, str]]]:
		project_id = project.get("ProjectId", "")
		data_sources_payload: dict[str, dict[str, str]] = {}
		excel_data_sources_payload: dict[str, dict[str, str]] = {}
		single_text_file_sources_payload: dict[str, dict[str, str]] = {}

		for business_unit in self.ctx.business_units_by_project.get(project_id, []):
			business_unit_id = business_unit.get("BusinessUnitId", "")
			for data_source in sorted(
				self.ctx.data_sources_by_business_unit.get(business_unit_id, []),
				key=lambda item: item.get("Name", ""),
			):
				data_source_id = data_source.get("DataSourceId", "")
				base_name = data_source.get("Name") or data_source_id or "Unnamed DataSource"
				key_name = base_name
				if key_name in data_sources_payload and data_source_id:
					key_name = f"{base_name}_{data_source_id}"

				data_sources_payload[key_name] = {
					**dict(data_source),
					"BusinessUnitName": self.ctx.business_unit_names_by_id.get(
						business_unit_id,
						business_unit_id,
					),
					"DataSourceQueryTables": self.build_data_source_query_tables_payload(data_source_id),
				}

		for excel_data_source in sorted(
			self.ctx.excel_data_sources,
			key=lambda item: item.get("FileName", ""),
		):
			excel_id = excel_data_source.get("ExcelDataSourceId", "")
			base_name = excel_data_source.get("FileName") or excel_id or "Unnamed Excel Source"
			key_name = base_name
			if key_name in excel_data_sources_payload and excel_id:
				key_name = f"{base_name}_{excel_id}"

			excel_data_sources_payload[key_name] = dict(excel_data_source)

		for single_text_file_source in sorted(
			self.ctx.single_text_file_sources,
			key=lambda item: item.get("FileName", ""),
		):
			source_id = single_text_file_source.get("SingleTextFileSourceId", "")
			base_name = (
				single_text_file_source.get("FileName")
				or source_id
				or "Unnamed SingleTextFileSource"
			)
			key_name = base_name
			if key_name in single_text_file_sources_payload and source_id:
				key_name = f"{base_name}_{source_id}"

			single_text_file_sources_payload[key_name] = dict(single_text_file_source)

		return {
			"DataSources": data_sources_payload,
			"ExcelDataSources": excel_data_sources_payload,
			"SingleTextFileSources": single_text_file_sources_payload,
			"ODXConnectDatasources": self.build_odx_connect_datasources_payload(),
			"CDataDataSources": self.build_cdata_data_sources_payload(),
		}

	def build_data_source_query_tables_payload(self, data_source_id: str) -> dict[str, dict[str, str]]:
		payload: dict[str, dict[str, str]] = {}
		for item in self.ctx.data_source_query_tables_by_source.get(data_source_id, []):
			item_id = item.get("DataSourceQueryTableId", "")
			key_name = item_id or f"DataSourceQueryTable_{len(payload) + 1}"
			payload[key_name] = dict(item)
		return payload

	def build_odx_connect_datasources_payload(self) -> dict[str, dict[str, str]]:
		payload: dict[str, dict[str, str]] = {}
		for item in sorted(self.ctx.odx_connect_datasources, key=lambda i: i.get("Name", "")):
			item_id = item.get("ConnectODXDatasourceId", "")
			base_name = item.get("Name") or item_id or "Unnamed ODXConnectDatasource"
			key_name = base_name
			if key_name in payload and item_id:
				key_name = f"{base_name}_{item_id}"
			payload[key_name] = dict(item)
		return payload

	def build_cdata_data_sources_payload(self) -> dict[str, dict[str, str]]:
		payload: dict[str, dict[str, str]] = {}
		for item in sorted(self.ctx.cdata_data_sources, key=lambda i: i.get("ProviderName", "")):
			item_id = item.get("CDataDataSourceId", "")
			base_name = item.get("ProviderName") or item_id or "Unnamed CDataDataSource"
			key_name = base_name
			if key_name in payload and item_id:
				key_name = f"{base_name}_{item_id}"
			payload[key_name] = dict(item)
		return payload

	def build_semantic_layer_hierarchies_payload(self, sl_table_id: str) -> dict[str, dict[str, object]]:
		hierarchies_payload: dict[str, dict[str, object]] = {}
		for hierarchy in sorted(
			self.ctx.semantic_layer_hierarchies_by_sl_table.get(sl_table_id, []),
			key=lambda item: item.get("Name", ""),
		):
			hierarchy_id = hierarchy.get("SemanticLayerHierarchyId", "")
			hierarchy_name = hierarchy.get("Name") or hierarchy_id or "Unnamed SemanticLayerHierarchy"
			key_name = hierarchy_name
			if key_name in hierarchies_payload and hierarchy_id:
				key_name = f"{hierarchy_name}_{hierarchy_id}"
			hierarchies_payload[key_name] = {
				**dict(hierarchy),
				"SemanticLayerHierarchyFields": self.build_semantic_layer_hierarchy_fields_payload(hierarchy_id),
			}
		return hierarchies_payload

	def build_semantic_layer_hierarchy_fields_payload(self, hierarchy_id: str) -> dict[str, dict[str, str]]:
		fields_payload: dict[str, dict[str, str]] = {}
		for hf in sorted(
			self.ctx.semantic_layer_hierarchy_fields_by_hierarchy.get(hierarchy_id, []),
			key=lambda item: item.get("Name", ""),
		):
			hf_id = hf.get("SemanticLayerHierarchyFieldId", "")
			hf_name = hf.get("Name") or hf_id or "Unnamed SemanticLayerHierarchyField"
			key_name = hf_name
			if key_name in fields_payload and hf_id:
				key_name = f"{hf_name}_{hf_id}"
			sl_field_id = hf.get("SemanticLayerFieldId", "")
			fields_payload[key_name] = {
				**dict(hf),
				"SemanticLayerFieldName": self.ctx.semantic_layer_field_names_by_id.get(
					sl_field_id, sl_field_id
				),
			}
		return fields_payload

	def build_semantic_layer_security_setups_payload(self, sl_field_id: str) -> dict[str, dict[str, object]]:
		setups_payload: dict[str, dict[str, object]] = {}
		for setup in self.ctx.semantic_layer_security_setups_by_sl_field.get(sl_field_id, []):
			setup_id = setup.get("SemanticLayerSecuritySetupId", "")
			setup_name = setup.get("Name") or setup_id or "Unnamed SemanticLayerSecuritySetup"
			key_name = setup_name
			if key_name in setups_payload and setup_id:
				key_name = f"{setup_name}_{setup_id}"
			setups_payload[key_name] = {
				**dict(setup),
				"SemanticLayerSecuritySetupRelations": self.build_semantic_layer_security_setup_relations_payload(setup_id),
				"SemanticLayerDynamicSecuritySetupItems": self.build_semantic_layer_dynamic_security_setup_items_payload(setup_id),
			}
		return setups_payload

	def build_semantic_layer_security_setup_relations_payload(self, setup_id: str) -> dict[str, dict[str, str]]:
		payload: dict[str, dict[str, str]] = {}
		for rel in self.ctx.semantic_layer_security_setup_relations_by_setup.get(setup_id, []):
			rel_id = rel.get("SemanticLayerSecuritySetupRelationId", "")
			key_name = rel_id or f"SemanticLayerSecuritySetupRelation_{len(payload) + 1}"
			payload[key_name] = dict(rel)
		return payload

	def build_semantic_layer_dynamic_security_setup_items_payload(self, setup_id: str) -> dict[str, dict[str, str]]:
		payload: dict[str, dict[str, str]] = {}
		for item in self.ctx.semantic_layer_dynamic_security_setup_items_by_setup.get(setup_id, []):
			item_id = item.get("SemanticLayerDynamicSecuritySetupId", "")
			key_name = item_id or f"SemanticLayerDynamicSecuritySetupItem_{len(payload) + 1}"
			security_table_id = item.get("SecurityDataTableId", "")
			values_field_id = item.get("ValuesDataFieldId", "")
			role_members_field_id = item.get("RoleMembersDataFieldId", "")
			payload[key_name] = {
				**dict(item),
				"SecurityDataTableName": self.ctx.table_names_by_id.get(security_table_id, security_table_id),
				"ValuesDataFieldName": self.ctx.field_names_by_id.get(values_field_id, values_field_id),
				"RoleMembersDataFieldName": self.ctx.field_names_by_id.get(role_members_field_id, role_members_field_id),
			}
		return payload

	def build_semantic_layer_models_payload(self, project: dict[str, str]) -> dict[str, dict[str, object]]:
		project_id = project.get("ProjectId", "")
		models_payload: dict[str, dict[str, object]] = {}
		for model in sorted(
			self.ctx.semantic_layer_models_by_project.get(project_id, []),
			key=lambda item: item.get("Name", ""),
		):
			model_id = model.get("SemanticLayerModelId", "")
			model_name = model.get("Name") or model_id or "Unnamed SemanticLayerModel"
			key_name = model_name
			if key_name in models_payload and model_id:
				key_name = f"{model_name}_{model_id}"
			models_payload[key_name] = {
				**dict(model),
				"SemanticLayerTables": self.build_semantic_layer_tables_payload(model_id),
				"SemanticLayerRelations": self.build_semantic_layer_relations_payload(model_id),
			}
		return models_payload

	def build_semantic_layer_tables_payload(self, model_id: str) -> dict[str, dict[str, object]]:
		tables_payload: dict[str, dict[str, object]] = {}
		for sl_table in sorted(
			self.ctx.semantic_layer_tables_by_model.get(model_id, []),
			key=lambda item: item.get("Name", ""),
		):
			sl_table_id = sl_table.get("SemanticLayerTableId", "")
			sl_table_name = sl_table.get("Name") or sl_table_id or "Unnamed SemanticLayerTable"
			key_name = sl_table_name
			if key_name in tables_payload and sl_table_id:
				key_name = f"{sl_table_name}_{sl_table_id}"
			table_id = sl_table.get("TableId", "")
			tables_payload[key_name] = {
				**dict(sl_table),
				"TableName": self.ctx.table_names_by_id.get(table_id, table_id),
				"SemanticLayerFields": self.build_semantic_layer_fields_payload(sl_table_id),
				"SemanticLayerHierarchies": self.build_semantic_layer_hierarchies_payload(sl_table_id),
				"SemanticLayerSelectionRules": self.build_semantic_layer_selection_rules_payload(sl_table_id),
				"SemanticLayerMeasures": self.build_semantic_layer_measures_payload(sl_table_id),
			}
		return tables_payload

	def build_semantic_layer_fields_payload(self, sl_table_id: str) -> dict[str, dict[str, str]]:
		fields_payload: dict[str, dict[str, str]] = {}
		for sl_field in sorted(
			self.ctx.semantic_layer_fields_by_sl_table.get(sl_table_id, []),
			key=lambda item: item.get("Name", ""),
		):
			sl_field_id = sl_field.get("SemanticLayerFieldId", "")
			sl_field_name = sl_field.get("Name") or sl_field_id or "Unnamed SemanticLayerField"
			key_name = sl_field_name
			if key_name in fields_payload and sl_field_id:
				key_name = f"{sl_field_name}_{sl_field_id}"
			field_id = sl_field.get("FieldId", "")
			sort_by_field_id = sl_field.get("SortByFieldId", "")
			fields_payload[key_name] = {
				**dict(sl_field),
				"FieldName": self.ctx.field_names_by_id.get(field_id, field_id),
				"SortByFieldName": self.ctx.semantic_layer_field_names_by_id.get(
					sort_by_field_id, sort_by_field_id
				) if sort_by_field_id else "",
				"SemanticLayerSecuritySetups": self.build_semantic_layer_security_setups_payload(sl_field_id),
			}
		return fields_payload

	def build_semantic_layer_relations_payload(self, model_id: str) -> dict[str, dict[str, object]]:
		relations_payload: dict[str, dict[str, object]] = {}
		for relation in sorted(
			self.ctx.semantic_layer_relations_by_model.get(model_id, []),
			key=lambda item: item.get("Name", ""),
		):
			relation_id = relation.get("SemanticLayerRelationId", "")
			relation_name = relation.get("Name") or relation_id or "Unnamed SemanticLayerRelation"
			key_name = relation_name
			if key_name in relations_payload and relation_id:
				key_name = f"{relation_name}_{relation_id}"
			relations_payload[key_name] = {
				**dict(relation),
				"SemanticLayerRelationItems": self.build_semantic_layer_relation_items_payload(relation_id),
			}
		return relations_payload

	def build_semantic_layer_relation_items_payload(self, relation_id: str) -> dict[str, dict[str, str]]:
		items_payload: dict[str, dict[str, str]] = {}
		for item in self.ctx.semantic_layer_relation_items_by_relation.get(relation_id, []):
			item_id = item.get("SemanticLayerRelationItemId", "")
			key_name = item_id or f"SemanticLayerRelationItem_{len(items_payload) + 1}"
			field_id = item.get("FieldId", "")
			referenced_field_id = item.get("ReferencedFieldId", "")
			items_payload[key_name] = {
				**dict(item),
				"FieldName": self.ctx.semantic_layer_field_names_by_id.get(
					field_id, self.ctx.field_names_by_id.get(field_id, field_id)
				),
				"ReferencedFieldName": self.ctx.semantic_layer_field_names_by_id.get(
					referenced_field_id, self.ctx.field_names_by_id.get(referenced_field_id, referenced_field_id)
				),
			}
		return items_payload

	def build_semantic_layer_selection_rules_payload(self, sl_table_id: str) -> dict[str, dict[str, object]]:
		rules_payload: dict[str, dict[str, object]] = {}
		for rule in self.ctx.semantic_layer_selection_rules_by_sl_table.get(sl_table_id, []):
			rule_id = rule.get("SemanticLayerSelectionRuleId", "")
			key_name = rule_id or f"SemanticLayerSelectionRule_{len(rules_payload) + 1}"
			rules_payload[key_name] = {
				**dict(rule),
				"SemanticLayerSelectionRuleFields": self.build_semantic_layer_selection_rule_fields_payload(rule_id),
			}
		return rules_payload

	def build_semantic_layer_selection_rule_fields_payload(self, rule_id: str) -> dict[str, dict[str, str]]:
		fields_payload: dict[str, dict[str, str]] = {}
		for srf in self.ctx.semantic_layer_selection_rule_fields_by_rule.get(rule_id, []):
			srf_id = srf.get("SemanticLayerSelectionRuleFieldId", "")
			key_name = srf_id or f"SemanticLayerSelectionRuleField_{len(fields_payload) + 1}"
			sl_field_id = srf.get("SemanticLayerFieldId", "")
			fields_payload[key_name] = {
				**dict(srf),
				"SemanticLayerFieldName": self.ctx.semantic_layer_field_names_by_id.get(
					sl_field_id, sl_field_id
				),
			}
		return fields_payload

	def build_semantic_layer_measures_payload(self, sl_table_id: str) -> dict[str, dict[str, object]]:
		measures_payload: dict[str, dict[str, object]] = {}
		for measure in sorted(
			self.ctx.semantic_layer_measures_by_sl_table.get(sl_table_id, []),
			key=lambda item: item.get("Name", ""),
		):
			measure_id = measure.get("SemanticLayerMeasureId", "")
			measure_name = measure.get("Name") or measure_id or "Unnamed SemanticLayerMeasure"
			key_name = measure_name
			if key_name in measures_payload and measure_id:
				key_name = f"{measure_name}_{measure_id}"
			sl_field_id = measure.get("SemanticLayerFieldId", "")
			measures_payload[key_name] = {
				**dict(measure),
				"SemanticLayerFieldName": self.ctx.semantic_layer_field_names_by_id.get(
					sl_field_id, sl_field_id
				) if sl_field_id else "",
				"SemanticLayerMeasureCustomScripts": self.build_semantic_layer_measure_custom_scripts_payload(measure_id),
			}
		return measures_payload

	def build_semantic_layer_measure_custom_scripts_payload(self, measure_id: str) -> dict[str, dict[str, str]]:
		scripts_payload: dict[str, dict[str, str]] = {}
		for script in self.ctx.semantic_layer_measure_custom_scripts_by_measure.get(measure_id, []):
			script_id = script.get("SemanticLayerMeasureCustomScriptId", "")
			script_name = script.get("Name") or script_id or f"Script_{len(scripts_payload) + 1}"
			key_name = script_name
			if key_name in scripts_payload and script_id:
				key_name = f"{script_name}_{script_id}"
			scripts_payload[key_name] = dict(script)
		return scripts_payload

	def build_warehouses_payload(self, project: dict[str, str]) -> dict[str, dict[str, object]]:
		project_id = project.get("ProjectId", "")
		warehouses_payload: dict[str, dict[str, object]] = {}

		for warehouse in sorted(
			self.ctx.warehouses_by_project.get(project_id, []),
			key=lambda item: item.get("Name", ""),
		):
			warehouse_name = (
				warehouse.get("Name")
				or warehouse.get("DataWarehouseId")
				or "Unnamed Warehouse"
			)
			warehouses_payload[warehouse_name] = self.build_single_warehouse_payload(warehouse)

		return warehouses_payload

	def build_single_warehouse_payload(
		self,
		warehouse: dict[str, str],
	) -> dict[str, object]:
		tables_payload: dict[str, dict[str, object]] = {}
		views_payload: dict[str, dict[str, object]] = {}

		for table in self.iter_warehouse_tables(warehouse):
			table_id = table.get("DataTableId", "")
			table_name = table.get("Name") or table_id or "Unnamed Table"

			table_payload = with_nested_properties(
				table,
				DataWarehouseMappingTables=self.build_mapping_tables_payload(table_id),
				SelectionRules=self.build_table_level_selection_rules_payload(table_id),
				Fields=self.build_fields_payload(table_id),
				LookupFields=self.build_lookup_fields_payload(table_id),
				Transformations=self.build_transformations_payload(table_id),
				BusinessFunctionUsers=self.build_bfus_for_table_payload(table_id),
				RelatedRecords=self.build_related_records_payload(table_id),
				DataRelations=self.build_relations_payload(table_id),
				TableInserts=self.build_table_inserts_payload(table_id),
				CustomHashFields=self.build_custom_hash_fields_payload(table_id),
				AggregateTableFields=self.build_aggregate_table_fields_payload(table_id),
			)

			if table_id in self.ctx.view_ids:
				views_payload[table_name] = with_nested_properties(
					table_payload,
					ViewProperties=dict(self.ctx.views_by_id.get(table_id, {})),
					ViewDefinitions=dict(
						self.ctx.view_definitions_by_id.get(table_id, {})
					),
				)
			else:
				tables_payload[table_name] = table_payload

		return with_nested_properties(
			warehouse,
			Tables=tables_payload,
			Views=views_payload,
		)

	def iter_warehouse_tables(self, warehouse: dict[str, str]) -> list[dict[str, str]]:
		warehouse_id = warehouse.get("DataWarehouseId", "")
		all_tables: list[dict[str, str]] = []

		for connection in self.ctx.connections_by_warehouse.get(warehouse_id, []):
			connection_id = connection.get("SqlServerConnectionId", "")
			all_tables.extend(self.ctx.tables_by_connection.get(connection_id, []))

		return sorted(all_tables, key=lambda item: item.get("Name", ""))

	def build_fields_payload(self, table_id: str) -> dict[str, dict[str, str]]:
		fields_payload: dict[str, dict[str, object]] = {}
		for field in sorted(
			self.ctx.fields_by_table.get(table_id, []),
			key=lambda item: item.get("Name", ""),
		):
			field_id = field.get("DataFieldId", "")
			field_name = field.get("Name") or field_id or "Unnamed Field"
			field_payload: dict[str, object] = {
				**dict(field),
				"DataMovementRelations": self.build_data_movement_relations_payload(field_id),
			}
			aliases = self.ctx.field_aliases_by_id.get(field_id, [])
			if aliases:
				field_payload["Aliases"] = aliases
			fields_payload[field_name] = field_payload
		return fields_payload

	def build_data_movement_relations_payload(
		self,
		destination_field_id: str,
	) -> dict[str, dict[str, str]]:
		relations_payload: dict[str, dict[str, str]] = {}
		for relation in sorted(
			self.ctx.data_movement_relations_by_destination_field.get(destination_field_id, []),
			key=lambda item: item.get("DataMovementRelationId", ""),
		):
			relation_id = relation.get("DataMovementRelationId", "")
			key_name = relation_id or f"DataMovementRelation_{len(relations_payload) + 1}"
			source_field_id = relation.get("SourceDataFieldId", "")
			destination_id = relation.get("DestinationDataFieldId", "")
			source_table_id = self.ctx.field_table_by_id.get(source_field_id, "")
			source_warehouse_id = self.ctx.table_warehouse_by_id.get(source_table_id, "")
			source_schema_name = self.ctx.table_schema_by_id.get(source_table_id, "")
			source_schema_or_warehouse_name = source_schema_name or self.ctx.warehouse_names_by_id.get(
				source_warehouse_id,
				source_warehouse_id,
			)
			relations_payload[key_name] = {
				**dict(relation),
				"SourceDataFieldName": self.ctx.field_names_by_id.get(
					source_field_id,
					source_field_id,
				),
				"DestinationDataFieldName": self.ctx.field_names_by_id.get(
					destination_id,
					destination_id,
				),
				"SourceDataTableName": self.ctx.table_names_by_id.get(
					source_table_id,
					source_table_id,
				),
				"SourceDataSchemaName": source_schema_or_warehouse_name,
			}
		return relations_payload

	def build_relations_payload(self, table_id: str) -> list[dict[str, str]]:
		return [
			{
				**dict(relation),
				"PrimaryDataTableName": self.ctx.table_names_by_id.get(
					relation.get("PrimaryDataTableId", ""),
					relation.get("PrimaryDataTableId", ""),
				),
				"SecondaryDataTableName": self.ctx.table_names_by_id.get(
					relation.get("SecondaryDataTableId", ""),
					relation.get("SecondaryDataTableId", ""),
				),
			}
			for relation in self.ctx.relations_by_table.get(table_id, [])
		]

	def build_mapping_tables_payload(self, destination_table_id: str) -> dict[str, dict[str, str]]:
		mapping_payload: dict[str, dict[str, object]] = {}
		for mapping in sorted(
			self.ctx.mapping_tables_by_destination_table.get(destination_table_id, []),
			key=lambda item: item.get("SeqNo", ""),
		):
			mapping_id = mapping.get("DataWarehouseMappingTableId", "")
			key_name = mapping_id or f"DataWarehouseMappingTable_{len(mapping_payload) + 1}"
			source_table_id = mapping.get("SourceTableId", "")
			destination_id = mapping.get("DestinationTableId", "")
			source_schema_name = self.ctx.table_schema_by_id.get(source_table_id, "")
			source_warehouse_id = self.ctx.table_warehouse_by_id.get(source_table_id, "")
			source_schema_or_warehouse_name = source_schema_name or self.ctx.warehouse_names_by_id.get(
				source_warehouse_id,
				source_warehouse_id,
			)
			mapping_payload[key_name] = {
				**dict(mapping),
				"SourceTableName": self.ctx.table_names_by_id.get(
					source_table_id,
					source_table_id,
				),
				"SourceSchemaName": source_schema_or_warehouse_name,
				"DestinationTableName": self.ctx.table_names_by_id.get(
					destination_id,
					destination_id,
				),
				"SelectionRules": self.build_selection_rules_payload(mapping_id),
			}
		return mapping_payload

	def build_table_level_selection_rules_payload(self, table_id: str) -> dict[str, dict[str, object]]:
		rules_payload: dict[str, dict[str, object]] = {}
		for rule in sorted(
			self.ctx.selection_rules_by_table.get(table_id, []),
			key=lambda item: item.get("SeqNo", ""),
		):
			rule_id = rule.get("SelectionRuleId", "")
			key_name = rule_id or f"SelectionRule_{len(rules_payload) + 1}"
			rules_payload[key_name] = {
				**dict(rule),
				"SelectionRuleFields": self.build_selection_rule_fields_payload(rule_id),
			}
		return rules_payload

	def build_selection_rules_payload(
		self,
		mapping_table_id: str,
	) -> dict[str, dict[str, str]]:
		rules_payload: dict[str, dict[str, object]] = {}
		for rule in sorted(
			self.ctx.selection_rules_by_mapping_table.get(mapping_table_id, []),
			key=lambda item: item.get("SeqNo", ""),
		):
			rule_id = rule.get("SelectionRuleId", "")
			key_name = rule_id or f"SelectionRule_{len(rules_payload) + 1}"
			data_table_id = rule.get("DataTableId", "")
			rules_payload[key_name] = {
				**dict(rule),
				"DataTableName": self.ctx.table_names_by_id.get(
					data_table_id,
					data_table_id,
				),
				"SelectionRuleFields": self.build_selection_rule_fields_payload(rule_id),
			}
		return rules_payload

	def build_selection_rule_fields_payload(
		self,
		selection_rule_id: str,
	) -> dict[str, dict[str, str]]:
		fields_payload: dict[str, dict[str, str]] = {}
		for selection_rule_field in sorted(
			self.ctx.selection_rule_fields_by_rule.get(selection_rule_id, []),
			key=lambda item: item.get("SeqNo", ""),
		):
			selection_rule_field_id = selection_rule_field.get("SelectionRuleFieldId", "")
			key_name = selection_rule_field_id or f"SelectionRuleField_{len(fields_payload) + 1}"
			data_field_id = selection_rule_field.get("DataFieldId", "")
			fields_payload[key_name] = {
				**dict(selection_rule_field),
				"DataFieldName": self.ctx.field_names_by_id.get(data_field_id, data_field_id),
			}
		return fields_payload

	def build_related_records_payload(self, table_id: str) -> dict[str, dict[str, object]]:
		related_records_payload: dict[str, dict[str, object]] = {}
		for related_record in sorted(
			self.ctx.related_records_by_table.get(table_id, []),
			key=lambda item: item.get("ExecutionNo", ""),
		):
			related_record_id = related_record.get("RelatedRecordId", "")
			key_name = related_record_id or f"RelatedRecord_{len(related_records_payload) + 1}"
			lookup_table_id = related_record.get("LookupTableId", "")
			lookup_table_name = self.ctx.table_names_by_id.get(lookup_table_id, lookup_table_id)
			lookup_warehouse_id = self.ctx.table_warehouse_by_id.get(lookup_table_id, "")
			lookup_table_schema = self.ctx.warehouse_names_by_id.get(
				lookup_warehouse_id,
				"",
			) or self.ctx.table_schema_by_id.get(lookup_table_id, "")
			lookup_table_qualified_name = (
				f"{lookup_table_schema}.{lookup_table_name}"
				if lookup_table_schema
				else lookup_table_name
			)
			related_records_payload[key_name] = {
				**dict(related_record),
				"LookupTableName": lookup_table_name,
				"LookupTableSchemaName": lookup_table_schema,
				"LookupTableQualifiedName": lookup_table_qualified_name,
				"RelatedRecordMappingFields": self.build_related_record_mapping_fields_payload(
					related_record_id
				),
				"RelatedRecordRelations": self.build_related_record_relations_payload(
					related_record_id
				),
			}
		return related_records_payload

	def build_related_record_mapping_fields_payload(
		self,
		related_record_id: str,
	) -> dict[str, dict[str, str]]:
		mapping_fields_payload: dict[str, dict[str, str]] = {}
		for mapping_field in sorted(
			self.ctx.related_record_mapping_fields_by_record.get(related_record_id, []),
			key=lambda item: item.get("RelatedRecordMappingFieldId", ""),
		):
			mapping_field_id = mapping_field.get("RelatedRecordMappingFieldId", "")
			key_name = mapping_field_id or f"RelatedRecordMappingField_{len(mapping_fields_payload) + 1}"
			data_field_id = mapping_field.get("DataFieldId", "")
			mapped_data_field_id = mapping_field.get("MappedDataFieldId", "")
			mapping_fields_payload[key_name] = {
				**dict(mapping_field),
				"DataFieldName": self.ctx.field_names_by_id.get(data_field_id, data_field_id),
				"MappedDataFieldName": self.ctx.field_names_by_id.get(
					mapped_data_field_id,
					mapped_data_field_id,
				),
			}
		return mapping_fields_payload

	def build_related_record_relations_payload(
		self,
		related_record_id: str,
	) -> dict[str, dict[str, str]]:
		relations_payload: dict[str, dict[str, str]] = {}
		for relation in sorted(
			self.ctx.related_record_relations_by_record.get(related_record_id, []),
			key=lambda item: item.get("ExecutionNo", ""),
		):
			relation_id = relation.get("RelatedRecordRelationId", "")
			key_name = relation_id or f"RelatedRecordRelation_{len(relations_payload) + 1}"
			data_field_id = relation.get("DataFieldId", "")
			relations_payload[key_name] = {
				**dict(relation),
				"DataFieldName": self.ctx.field_names_by_id.get(data_field_id, data_field_id),
			}
		return relations_payload

	def build_transformations_payload(self, table_id: str) -> dict[str, dict[str, str]]:
		transformations_payload: dict[str, dict[str, object]] = {}
		for field in self.ctx.fields_by_table.get(table_id, []):
			field_id = field.get("DataFieldId", "")
			for transformation in self.ctx.transformations_by_field.get(field_id, []):
				transformation_id = transformation.get("TransformationId", "")
				transformation_name = (
					transformation.get("Name")
					or transformation_id
					or f"Transformation_{len(transformations_payload) + 1}"
				)

				key_name = transformation_name
				if key_name in transformations_payload and transformation_id:
					key_name = f"{transformation_name}_{transformation_id}"

				transformations_payload[key_name] = {
					**dict(transformation),
					"DataFieldName": self.ctx.field_names_by_id.get(
						field_id,
						field_id,
					),
					"Conditions": self.build_conditions_payload(
						self.ctx.conditions_by_transformation.get(transformation_id, [])
					),
				}

		return transformations_payload

	def build_lookup_fields_payload(self, table_id: str) -> dict[str, dict[str, object]]:
		lookup_fields_payload: dict[str, dict[str, object]] = {}
		for lookup_field in sorted(
			self.ctx.lookup_fields_by_table.get(table_id, []),
			key=lambda item: item.get("Name", ""),
		):
			lookup_field_id = lookup_field.get("LookupFieldId", "")
			key_name = lookup_field_id or f"LookupField_{len(lookup_fields_payload) + 1}"

			data_field_id = lookup_field.get("LookupDataFieldId", "")
			lookup_fields_payload[key_name] = {
				**dict(lookup_field),
				"LookupDataFieldName": self.ctx.field_names_by_id.get(
					data_field_id,
					data_field_id,
				),
				"ConditionalLookupFieldName": self.ctx.conditional_lookup_field_name_by_id.get(
					lookup_field.get("ConditionalLookupFieldId", ""),
					self.ctx.field_names_by_id.get(
						lookup_field.get("ConditionalLookupFieldId", ""),
						lookup_field.get("ConditionalLookupFieldId", ""),
					),
				),
				"Conditions": self.build_conditions_payload(
					self.ctx.conditions_by_lookup_field.get(lookup_field_id, [])
				),
				"Joins": self.build_joins_payload(
					self.ctx.joins_by_lookup_field.get(lookup_field_id, [])
				),
			}

		return lookup_fields_payload

	def build_conditions_payload(
		self,
		conditions: list[dict[str, str]],
	) -> dict[str, dict[str, str]]:
		conditions_payload: dict[str, dict[str, str]] = {}
		for condition in sorted(conditions, key=lambda item: item.get("SeqNo", "")):
			condition_id = condition.get("ConditionId", "")
			key_name = condition_id or f"Condition_{len(conditions_payload) + 1}"
			data_field_id = condition.get("DataFieldId", "")
			conditions_payload[key_name] = {
				**dict(condition),
				"DataFieldName": self.ctx.field_names_by_id.get(data_field_id, data_field_id),
			}
		return conditions_payload

	def build_joins_payload(
		self,
		joins: list[dict[str, str]],
	) -> dict[str, dict[str, str]]:
		joins_payload: dict[str, dict[str, str]] = {}
		for join in sorted(joins, key=lambda item: item.get("SeqNo", "")):
			join_id = join.get("JoinId", "")
			key_name = join_id or f"Join_{len(joins_payload) + 1}"
			primary_field_id = join.get("PrimaryDataFieldId", "")
			join_field_id = join.get("JoinDataFieldId", "")
			joins_payload[key_name] = {
				**dict(join),
				"PrimaryDataFieldName": self.ctx.field_names_by_id.get(
					primary_field_id,
					primary_field_id,
				),
				"JoinDataFieldName": self.ctx.field_names_by_id.get(
					join_field_id,
					join_field_id,
				),
			}
		return joins_payload

	def build_business_function_users_payload(
		self,
		project: dict[str, str],
	) -> dict[str, dict[str, object]]:
		project_id = project.get("ProjectId", "")
		bfu_payload: dict[str, dict[str, object]] = {}
		for bfu in sorted(
			self.ctx.business_function_users_by_project.get(project_id, []),
			key=lambda item: item.get("BusinessFunctionName", ""),
		):
			bfu_id = bfu.get("BusinessFunctionUserId", "")
			bfu_name = bfu.get("BusinessFunctionName") or bfu_id or "Unnamed BFU"
			key_name = bfu_name
			if key_name in bfu_payload and bfu_id:
				key_name = f"{bfu_name}_{bfu_id}"
			params = self.ctx.business_function_user_parameters_by_user.get(bfu_id, [])
			bfu_payload[key_name] = {
				**dict(bfu),
				"BusinessFunctionScriptTranslated": self.translate_bfu_script(
					bfu.get("BusinessFunctionScript", ""), params
				),
				"Conditions": self.build_conditions_payload(self.ctx.conditions_by_bfu.get(bfu_id, [])),
				"BusinessFunctionUserParameters": self.build_bfu_parameters_payload(bfu_id),
				"BusinessFunctionUserValues": self.build_bfu_values_payload(bfu_id),
			}
		return bfu_payload

	def translate_bfu_script(
		self,
		script: str,
		params: list[dict[str, str]],
	) -> str:
		"""Replace @ParameterName placeholders in BusinessFunctionScript with resolved values."""
		result = script
		for param in sorted(params, key=lambda p: p.get("BusinessFunctionParameterOrdinal", "")):
			param_name = param.get("BusinessFunctionParameterName", "")
			if not param_name:
				continue
			param_type = param.get("BusinessFunctionParameterType", "")
			if param_type == "Field":
				tx_object_id = param.get("TXObjectId", "")
				field_name = self.ctx.field_names_by_id.get(tx_object_id, tx_object_id)
				replacement = f"[{field_name}]"
			elif param_type == "Value":
				replacement = param.get("Value", "")
			else:
				# Unknown types: keep visible so nothing is silently dropped
				replacement = f"<{param_type}:{param_name}>"
			result = result.replace(param_name, replacement)
		return result

	def build_bfus_for_table_payload(
		self,
		table_id: str,
	) -> dict[str, dict[str, object]]:
		bfu_payload: dict[str, dict[str, object]] = {}
		for bfu in sorted(
			self.ctx.bfus_by_table.get(table_id, []),
			key=lambda item: item.get("BusinessFunctionName", "") if item else "",
		):
			if not bfu:
				continue
			bfu_id = bfu.get("BusinessFunctionUserId", "")
			bfu_name = bfu.get("BusinessFunctionName") or bfu_id or "Unnamed BFU"
			key_name = bfu_name
			if key_name in bfu_payload and bfu_id:
				key_name = f"{bfu_name}_{bfu_id}"
			params = self.ctx.business_function_user_parameters_by_user.get(bfu_id, [])
			field_id = self.ctx.bfu_data_field_by_user.get(bfu_id, "")
			bfu_payload[key_name] = {
				**dict(bfu),
				"DataFieldName": self.ctx.field_names_by_id.get(field_id, field_id),
				"BusinessFunctionScriptTranslated": self.translate_bfu_script(
					bfu.get("BusinessFunctionScript", ""), params
				),
				"Conditions": self.build_conditions_payload(self.ctx.conditions_by_bfu.get(bfu_id, [])),
				"BusinessFunctionUserParameters": self.build_bfu_parameters_payload(bfu_id),
				"BusinessFunctionUserValues": self.build_bfu_values_payload(bfu_id),
			}
		return bfu_payload

	def build_bfu_parameters_payload(self, bfu_id: str) -> dict[str, dict[str, object]]:
		params_payload: dict[str, dict[str, object]] = {}
		for param in sorted(
			self.ctx.business_function_user_parameters_by_user.get(bfu_id, []),
			key=lambda item: item.get("BusinessFunctionParameterOrdinal", ""),
		):
			param_id = param.get("BusinessFunctionUserParameterId", "")
			param_name = (
				param.get("BusinessFunctionParameterName") or param_id or "Unnamed Param"
			)
			key_name = param_name
			if key_name in params_payload and param_id:
				key_name = f"{param_name}_{param_id}"
			tx_object_id = param.get("TXObjectId", "")
			params_payload[key_name] = {
				**dict(param),
				"TXObjectName": self.ctx.field_names_by_id.get(tx_object_id, tx_object_id)
				if tx_object_id
				else "",
			}
		return params_payload

	def build_bfu_values_payload(self, bfu_id: str) -> dict[str, dict[str, str]]:
		values_payload: dict[str, dict[str, str]] = {}
		for value in sorted(
			self.ctx.business_function_user_values_by_user.get(bfu_id, []),
			key=lambda item: item.get("BusinessFunctionUserValueId", ""),
		):
			value_id = value.get("BusinessFunctionUserValueId", "")
			key_name = value_id or f"BFUValue_{len(values_payload) + 1}"
			values_payload[key_name] = dict(value)
		return values_payload

	def build_table_inserts_payload(
		self,
		destination_table_id: str,
	) -> dict[str, dict[str, object]]:
		inserts_payload: dict[str, dict[str, object]] = {}
		for insert in sorted(
			self.ctx.table_inserts_by_destination_table.get(destination_table_id, []),
			key=lambda item: item.get("Name", ""),
		):
			insert_id = insert.get("TableInsertId", "")
			insert_name = insert.get("Name") or insert_id or "Unnamed TableInsert"
			key_name = insert_name
			if key_name in inserts_payload and insert_id:
				key_name = f"{insert_name}_{insert_id}"
			source_table_id = insert.get("SourceTableId", "")
			source_schema_name = self.ctx.table_schema_by_id.get(source_table_id, "")
			source_warehouse_id = self.ctx.table_warehouse_by_id.get(source_table_id, "")
			source_schema_or_warehouse_name = (
				self.ctx.warehouse_names_by_id.get(source_warehouse_id, "")
				or source_schema_name
				or source_warehouse_id
			)
			inserts_payload[key_name] = {
				**dict(insert),
				"SourceTableName": self.ctx.table_names_by_id.get(
					source_table_id, source_table_id
				),
				"SourceSchemaName": source_schema_or_warehouse_name,
				"DestinationTableName": self.ctx.table_names_by_id.get(
					destination_table_id, destination_table_id
				),
				"TableInsertMappings": self.build_table_insert_mappings_payload(insert_id),
				"TableInsertSelectionRules": self.build_table_insert_selection_rules_payload(
					insert_id
				),
				"TableInsertScripts": self.build_table_insert_scripts_payload(insert_id),
			}
		return inserts_payload

	def build_table_insert_mappings_payload(
		self,
		insert_id: str,
	) -> dict[str, dict[str, str]]:
		mappings_payload: dict[str, dict[str, str]] = {}
		for mapping in sorted(
			self.ctx.table_insert_mappings_by_insert.get(insert_id, []),
			key=lambda item: item.get("TableInsertMappingId", ""),
		):
			mapping_id = mapping.get("TableInsertMappingId", "")
			key_name = mapping_id or f"TableInsertMapping_{len(mappings_payload) + 1}"
			dest_field_id = mapping.get("DestinationFieldId", "")
			source_field_id = mapping.get("SourceFieldId", "")
			mappings_payload[key_name] = {
				**dict(mapping),
				"DestinationFieldName": self.ctx.field_names_by_id.get(
					dest_field_id, dest_field_id
				),
				"SourceFieldName": self.ctx.field_names_by_id.get(
					source_field_id, source_field_id
				),
			}
		return mappings_payload

	def build_table_insert_selection_rules_payload(
		self,
		insert_id: str,
	) -> dict[str, dict[str, object]]:
		rules_payload: dict[str, dict[str, object]] = {}
		for rule in sorted(
			self.ctx.table_insert_selection_rules_by_insert.get(insert_id, []),
			key=lambda item: item.get("TableInsertSelectionRuleId", ""),
		):
			rule_id = rule.get("TableInsertSelectionRuleId", "")
			key_name = rule_id or f"TableInsertSelectionRule_{len(rules_payload) + 1}"
			rules_payload[key_name] = {
				**dict(rule),
				"TableInsertSelectionRuleFields": self.build_table_insert_selection_rule_fields_payload(
					rule_id
				),
			}
		return rules_payload

	def build_table_insert_selection_rule_fields_payload(
		self,
		rule_id: str,
	) -> dict[str, dict[str, str]]:
		fields_payload: dict[str, dict[str, str]] = {}
		for srf in sorted(
			self.ctx.table_insert_selection_rule_fields_by_rule.get(rule_id, []),
			key=lambda item: item.get("TableInsertSelectionRuleFieldId", ""),
		):
			srf_id = srf.get("TableInsertSelectionRuleFieldId", "")
			key_name = srf_id or f"TableInsertSelectionRuleField_{len(fields_payload) + 1}"
			data_field_id = srf.get("DataFieldId", "")
			fields_payload[key_name] = {
				**dict(srf),
				"DataFieldName": self.ctx.field_names_by_id.get(data_field_id, data_field_id),
			}
		return fields_payload

	def build_table_insert_scripts_payload(self, insert_id: str) -> dict[str, dict[str, str]]:
		payload: dict[str, dict[str, str]] = {}
		for script in self.ctx.table_insert_scripts_by_insert.get(insert_id, []):
			script_id = script.get("TableInsertScriptId", "")
			key_name = script_id or f"TableInsertScript_{len(payload) + 1}"
			payload[key_name] = dict(script)
		return payload

	def build_custom_hash_fields_payload(self, table_id: str) -> dict[str, list[str]]:
		items = self.ctx.custom_hash_field_items_by_table.get(table_id, [])
		grouped: dict[str, list[str]] = {}
		for item in items:
			host_field_id = item.get("CustomHasFieldId", "")
			hash_field_id = item.get("DataFieldId", "")
			if not host_field_id or not hash_field_id:
				continue
			host_field_name = self.ctx.field_names_by_id.get(host_field_id, host_field_id)
			hash_field_name = self.ctx.field_names_by_id.get(hash_field_id, hash_field_id)
			grouped.setdefault(host_field_name, []).append(hash_field_name)
		return grouped

	def build_aggregate_table_fields_payload(self, table_id: str) -> dict[str, dict[str, str]]:
		items = self.ctx.aggregate_table_fields_by_table.get(table_id, [])
		payload: dict[str, dict[str, str]] = {}
		for item in items:
			item_id = item.get("AggregateTableFieldId", "")
			key_name = item_id or f"AggregateTableField_{len(payload) + 1}"
			host_field_id = item.get("DataFieldId", "")
			related_field_id = item.get("RelatedDataFieldId", "")
			payload[key_name] = {
				**dict(item),
				"DataFieldName": self.ctx.field_names_by_id.get(host_field_id, host_field_id),
				"RelatedDataFieldName": self.ctx.field_names_by_id.get(related_field_id, related_field_id),
			}
		return payload

	def build_usage_summary(self) -> list[tuple[str, int, int]]:
		"""Return (entity_name, placed_count, total_count) for every indexed entity."""
		def placed(*dicts: dict) -> int:
			return len({id(rec) for d in dicts for recs in d.values() for rec in recs})

		return [
			("DataTables",                          len({t.get("DataTableId") for t in self.ctx.data_tables if t.get("SqlServerConnectionId") or t.get("DataSourceId") or t.get("ConnectODXId")}),                                       len(self.ctx.data_tables)),
			("DataFields",                          placed(self.ctx.fields_by_table),                                                                                   len(self.ctx.data_fields)),
			("Transformations",                     placed(self.ctx.transformations_by_field),                                                                          len(self.ctx.transformations)),
		("Conditions",                          placed(self.ctx.conditions_by_lookup_field, self.ctx.conditions_by_transformation, self.ctx.conditions_by_bfu),         len(self.ctx.conditions)),
			("Joins",                               placed(self.ctx.joins_by_lookup_field),                                                                             len(self.ctx.joins)),
			("LookupFields",                        placed(self.ctx.lookup_fields_by_table),                                                                            len(self.ctx.lookup_fields)),
			("DataMovementRelations",               placed(self.ctx.data_movement_relations_by_destination_field),                                                      len(self.ctx.data_movement_relations)),
			("DataWarehouseMappingTables",          placed(self.ctx.mapping_tables_by_destination_table),                                                               len(self.ctx.data_warehouse_mapping_tables)),
		("SelectionRules",                      placed(self.ctx.selection_rules_by_mapping_table, self.ctx.selection_rules_by_table),                                  len(self.ctx.selection_rules)),
			("SelectionRuleFields",                 placed(self.ctx.selection_rule_fields_by_rule),                                                                     len(self.ctx.selection_rule_fields)),
			("DataRelations",                       placed(self.ctx.relations_by_table),                                                                                len(self.ctx.data_relations)),
			("RelatedRecords",                      placed(self.ctx.related_records_by_table),                                                                          len(self.ctx.related_records)),
			("RelatedRecordMappingFields",          placed(self.ctx.related_record_mapping_fields_by_record),                                                           len(self.ctx.related_record_mapping_fields)),
			("RelatedRecordRelations",              placed(self.ctx.related_record_relations_by_record),                                                                len(self.ctx.related_record_relations)),
			("Views",                               len(self.ctx.view_ids),                                                                                             len(self.ctx.views)),
			("TableInserts",                        placed(self.ctx.table_inserts_by_destination_table),                                                                len(self.ctx.table_inserts)),
			("TableInsertMappings",                 placed(self.ctx.table_insert_mappings_by_insert),                                                                   len(self.ctx.table_insert_mappings)),
			("TableInsertSelectionRules",           placed(self.ctx.table_insert_selection_rules_by_insert),                                                            len(self.ctx.table_insert_selection_rules)),
			("TableInsertSelectionRuleFields",      placed(self.ctx.table_insert_selection_rule_fields_by_rule),                                                        len(self.ctx.table_insert_selection_rule_fields)),
			("TableInsertScripts",                  placed(self.ctx.table_insert_scripts_by_insert),                                                                    len(self.ctx.table_insert_scripts)),
			("CustomHashFieldItems",                placed(self.ctx.custom_hash_field_items_by_table),                                                                  len(self.ctx.custom_hash_field_items)),
			("AggregateTableFields",                placed(self.ctx.aggregate_table_fields_by_table),                                                                   len(self.ctx.aggregate_table_fields)),
			("DataSourceQueryTables",               placed(self.ctx.data_source_query_tables_by_source),                                                                len(self.ctx.data_source_query_tables)),
			("SemanticLayerTables",                 placed(self.ctx.semantic_layer_tables_by_model),                                                                    len(self.ctx.semantic_layer_tables)),
			("SemanticLayerFields",                 placed(self.ctx.semantic_layer_fields_by_sl_table),                                                                 len(self.ctx.semantic_layer_fields)),
			("SemanticLayerRelations",              placed(self.ctx.semantic_layer_relations_by_model),                                                                 len(self.ctx.semantic_layer_relations)),
			("SemanticLayerRelationItems",          placed(self.ctx.semantic_layer_relation_items_by_relation),                                                         len(self.ctx.semantic_layer_relation_items)),
			("SemanticLayerSelectionRules",         placed(self.ctx.semantic_layer_selection_rules_by_sl_table),                                                        len(self.ctx.semantic_layer_selection_rules)),
			("SemanticLayerSelectionRuleFields",    placed(self.ctx.semantic_layer_selection_rule_fields_by_rule),                                                      len(self.ctx.semantic_layer_selection_rule_fields)),
			("SemanticLayerMeasures",               placed(self.ctx.semantic_layer_measures_by_sl_table),                                                               len(self.ctx.semantic_layer_measures)),
			("SemanticLayerMeasureCustomScripts",   placed(self.ctx.semantic_layer_measure_custom_scripts_by_measure),                                                  len(self.ctx.semantic_layer_measure_custom_scripts)),
			("SemanticLayerHierarchies",            placed(self.ctx.semantic_layer_hierarchies_by_sl_table),                                                            len(self.ctx.semantic_layer_hierarchies)),
			("SemanticLayerHierarchyFields",        placed(self.ctx.semantic_layer_hierarchy_fields_by_hierarchy),                                                      len(self.ctx.semantic_layer_hierarchy_fields)),
			("SemanticLayerSecuritySetups",         placed(self.ctx.semantic_layer_security_setups_by_sl_field),                                                        len(self.ctx.semantic_layer_security_setups)),
			("SemanticLayerSecuritySetupRelations", placed(self.ctx.semantic_layer_security_setup_relations_by_setup),                                                  len(self.ctx.semantic_layer_security_setup_relations)),
			("SemanticLayerDynamicSecuritySetupItems", placed(self.ctx.semantic_layer_dynamic_security_setup_items_by_setup),                                           len(self.ctx.semantic_layer_dynamic_security_setup_items)),
		]

	@staticmethod
	def _group_by_key(
		records: list[dict[str, str]],
		key: str,
	) -> dict[str, list[dict[str, str]]]:
		grouped: dict[str, list[dict[str, str]]] = {}
		for record in records:
			group_key = record.get(key, "")
			if group_key:
				grouped.setdefault(group_key, []).append(record)
		return grouped

	@staticmethod
	def _build_lookup_by_id(
		records: list[dict[str, str]],
		id_key: str,
	) -> dict[str, dict[str, str]]:
		return {
			record.get(id_key, ""): record
			for record in records
			if record.get(id_key, "")
		}


def build_structure(root: ET.Element) -> dict[str, dict[str, object]]:
	builder = NestedJsonBuilder(root)
	return builder.build()


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Convert a TimeXtender XML export into a nested JSON summary."
	)
	parser.add_argument(
		"--input",
		default="ISD_DWH.XML",
		help="Path to input XML file (default: ISD_DWH.XML)",
	)
	parser.add_argument(
		"--output",
		default="ISD_DWH_nested.json",
		help="Path to output JSON file (default: ISD_DWH_nested.json)",
	)
	args = parser.parse_args()

	input_path = Path(args.input)
	output_path = Path(args.output)

	tree = ET.parse(input_path)
	root = tree.getroot()

	builder = NestedJsonBuilder(root)
	structure = builder.build()
	output_path.write_text(json.dumps(structure, indent=2), encoding="utf-8")

	print(f"JSON written to: {output_path.resolve()}")
	print()
	print("Usage Summary")
	print("=============")
	for name, used, total in builder.build_usage_summary():
		marker = " " if used == total else "!"
		print(f"  [{marker}] {name}: {used}/{total}")


if __name__ == "__main__":
	main()