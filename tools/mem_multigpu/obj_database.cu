#include <cstdint>
#include <cstring>
#include <iostream>

#include <adm_config.h>
#include <adm_common.h>
#include <adm_splay.h>
#include <adm_memory.h>
#include <adm_database.h>

using namespace adamant;

static adm_splay_tree_t* range_tree = nullptr;
static adm_hash_table_t* object_table; 
static pool_t<adm_splay_tree_t, ADM_DB_OBJ_BLOCKSIZE>* range_nodes = nullptr;
static pool_t<adm_range_t, ADM_DB_OBJ_BLOCKSIZE>* ranges = nullptr;
static pool_t<adm_object_t, ADM_DB_OBJ_BLOCKSIZE>* objects = nullptr;

void initialize_object_table(int size) {
	object_table = new adm_hash_table_t(size);
}

bool object_exists(uint64_t pc) {
	adm_object_t* obj = object_table->find(pc);
        if(obj) {
                return true;
        }
	return false;	
}

std::string get_object_var_name(uint64_t pc) {
	adm_object_t* obj = object_table->find(pc);
	if(obj) {
        	return obj->get_var_name();
	}
	return "";
}

std::string get_object_file_name(uint64_t pc) {
        adm_object_t* obj = object_table->find(pc);
        if(obj) {
                return obj->get_file_name();
        }
        return "";
}

std::string get_object_func_name(uint64_t pc) {
        adm_object_t* obj = object_table->find(pc);
        if(obj) {
                return obj->get_func_name();
        }
        return "";
}

uint32_t get_object_line_num(uint64_t pc) {
        adm_object_t* obj = object_table->find(pc);
        if(obj) {
                return obj->get_line_num();
        }
        return 0;
}

static inline
adm_splay_tree_t* adm_range_find_node(const uint64_t address) noexcept
{
  if(range_tree)
    return range_tree->find(address);
  return nullptr;
}

ADM_VISIBILITY
adm_range_t* adamant::adm_range_find(const uint64_t address) noexcept
{
  adm_splay_tree_t* node = adm_range_find_node(address);
  if(node) return node->range;
  return nullptr;
}

ADM_VISIBILITY 
adm_object_t* adamant::adm_object_insert(const uint64_t allocation_pc, std::string varname, std::string filename, std::string funcname, uint32_t linenum, const state_t state) noexcept
{
	adm_object_t* obj = object_table->find(allocation_pc);
	if(obj == nullptr) {
		obj = new adm_object_t();
		obj->set_allocation_pc(allocation_pc);
		obj->set_var_name(varname);
		obj->set_file_name(filename);
		obj->set_func_name(funcname);
		obj->set_line_num(linenum);
		object_table->insert(obj);
	}
	if(obj->get_allocation_pc() == allocation_pc)
                return obj;
	return nullptr;	
}

ADM_VISIBILITY
adm_range_t* adamant::adm_range_insert(const uint64_t address, const uint64_t size, const uint64_t allocation_pc, std::string var_name, const state_t state) noexcept
{
  adm_splay_tree_t* obj = nullptr;
  adm_splay_tree_t* pos = nullptr;

  //fprintf(stderr, "inside adm_range_insert before range_tree->find_with_parent\n");
  if(range_tree) range_tree->find_with_parent(address, pos, obj);
  //fprintf(stderr, "inside adm_range_insert after range_tree->find_with_parent\n");
  if(obj==nullptr) {
    //fprintf(stderr, "inside adm_range_insert before range_nodes->malloc\n");
    obj = range_nodes->malloc();
    if(obj==nullptr) return nullptr;

    //fprintf(stderr, "inside adm_range_insert before ranges->malloc\n");
    obj->range = ranges->malloc();
    if(obj->range==nullptr) return nullptr;

    obj->start = address;
    obj->range->set_address(address); 
    obj->end = obj->start+size;
    obj->range->set_size(size);
    obj->range->set_allocation_pc(allocation_pc);
    obj->range->set_var_name(var_name);
    obj->range->set_state(state);
    if(pos!=nullptr)
      pos->insert(obj);
    range_tree = obj->splay();
    //fprintf(stderr, "range is inserted to the splay tree\n");
  }
  else {
    if(!(obj->range->get_state()&ADM_STATE_FREE)) {
      if(obj->start==address)
        adm_warning("db_insert: address already in range_tree and not free - ", address);
      else if(obj->start<address && address<obj->end)
        adm_warning("db_insert: address in range of another address in range_tree - ", obj->start, "..", obj->end, " (", address, ")");
      if(obj->end<address+size) {
        obj->end = address+size;
        obj->range->set_size(size);
      }
      range_tree = obj->splay();
    }
    else {
      obj->range = ranges->malloc();
      if(obj->range==nullptr) return nullptr;

      obj->start = address;
      obj->range->set_address(address); 
      obj->end = obj->start+size;
      obj->range->set_size(size);
      obj->range->set_allocation_pc(allocation_pc);
      obj->range->set_var_name(var_name);
      obj->range->set_state(state);
      range_tree = obj->splay();
    }
  }

  return obj->range;
}

ADM_VISIBILITY
void adamant::adm_db_update_size(const uint64_t address, const uint64_t size) noexcept
{
  adm_splay_tree_t* obj = adm_range_find_node(address);
  if(obj) {
    obj->range->set_size(size);
    if(obj->start!=address) {
      adm_warning("db_update_size: address in range of another address in range_tree - ", obj->start, "..", obj->end, "(", address, ")");
      obj->start = address;
      obj->range->set_address(address);
    }
    obj->end = address+size;
    obj->range->set_size(size);
    range_tree = obj->splay();
  }
  else adm_warning("db_update_size: address not in range_tree - ", address);
}

ADM_VISIBILITY
void adamant::adm_db_update_state(const uint64_t address, const state_t state) noexcept
{
  adm_splay_tree_t* obj = adm_range_find_node(address);
  if(obj) {
    obj->range->add_state(state);
    if(obj->start!=address)
      adm_warning("db_update_state: address in range of another address in range_tree - ", obj->start, "..", obj->end, "(", address, ")");
  }
  else adm_warning("db_update_state: address not in range_tree - ", address);
}

ADM_VISIBILITY
void adamant::adm_ranges_print() noexcept
{
  //bool all = adm_conf_string("+all", "1");
  std::cout << "List of captured address ranges along with their variable names and code locations:\n";
  pool_t<adm_splay_tree_t, ADM_DB_OBJ_BLOCKSIZE>::iterator n(*range_nodes);
  for(adm_splay_tree_t* obj = n.next(); obj!=nullptr; obj = n.next())
    //if(obj->range->has_events())
    obj->range->print();
}

//#if 0
//ADM_VISIBILITY
void adamant::adm_db_init()
{
  range_nodes = new pool_t<adm_splay_tree_t, ADM_DB_OBJ_BLOCKSIZE>;
  ranges = new pool_t<adm_range_t, ADM_DB_OBJ_BLOCKSIZE>;
  objects = new pool_t<adm_object_t, ADM_DB_OBJ_BLOCKSIZE>;
}

//ADM_VISIBILITY
void adamant::adm_db_fini()
{
  delete range_nodes;
  delete ranges;
  delete objects;
}
//#endif

ADM_VISIBILITY
void adm_range_t::print() const noexcept
{
  //std::cout << "in adm_range_t::print\n";
  uint64_t a = get_address();
  std::cout << "offset: " << a << ", ";
  uint64_t z = get_size();
  std::cout << "size: " << z << ", ";
  uint64_t p = get_allocation_pc();
  adm_object_t* obj = object_table->find(p);
  obj->print();
#if 0
  uint64_t p = get_allocation_pc();
  std::cout << "allocation_pc: " << p << std::endl; 
#endif
  //std::string varname = get_var_name();
  //std::cout << varname << std::endl;
}

ADM_VISIBILITY
void adm_object_t::print() const noexcept
{
  //std::cout << "in adm_object_t::print\n";
  uint64_t p = get_allocation_pc();
  std::cout << "allocation_pc: " << p << ", "; 
  std::string varname = get_var_name();
  std::cout << "var_name: " << varname << ", ";
  std::string filename = get_file_name();
  std::cout << "file_name: " << filename << ", ";
  std::string funcname = get_func_name();
  std::cout << "func_name: " << funcname << ", ";
  uint32_t linenum = get_line_num();
  std::cout << "line_num: " << linenum << std::endl; 
}