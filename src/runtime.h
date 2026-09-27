#ifndef SIMPLE_RUNTIME_H
#define SIMPLE_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef enum {
    VAL_NIL,
    VAL_BOOL,
    VAL_INT,
    VAL_NUMBER,
    VAL_STRING,
    VAL_LIST,
    VAL_DICT,
    VAL_CLASS,
    VAL_INSTANCE,
    VAL_METHOD
} ValueType;

struct ObjString;
struct ObjList;
struct ObjDict;
struct ObjClass;
struct ObjInstance;
struct ObjMethod;

typedef struct Value {
    ValueType type;
    union {
        bool boolean;
        long long integer;
        double number;
        struct ObjString* string;
        struct ObjList* list;
        struct ObjDict* dict;
        struct ObjClass* klass;
        struct ObjInstance* instance;
        struct ObjMethod* method;
    } as;
} Value;

// String object
typedef struct ObjString {
    int length;
    char chars[];
} ObjString;

// List object
typedef struct ObjList {
    int count;
    int capacity;
    Value* items;
} ObjList;

// Dictionary entry & object
typedef struct DictEntry {
    char* key;
    Value value;
} DictEntry;

typedef struct ObjDict {
    int count;
    int capacity;
    DictEntry* entries;
} ObjDict;

// Method pointer type: receives this (receiver), arg_count, and args array
typedef Value (*MethodFn)(Value receiver, int arg_count, Value* args);

typedef struct MethodEntry {
    char* name;
    MethodFn fn;
} MethodEntry;

typedef struct ObjClass {
    char* name;
    struct ObjClass* superclass;
    int method_count;
    MethodEntry methods[64];
} ObjClass;

typedef struct FieldEntry {
    char* name;
    Value value;
} FieldEntry;

typedef struct ObjInstance {
    ObjClass* klass;
    int field_count;
    FieldEntry fields[64];
} ObjInstance;

typedef struct ObjMethod {
    Value receiver;
    MethodFn fn;
} ObjMethod;

// Constructors for values
static inline Value val_nil(void) {
    Value v;
    v.type = VAL_NIL;
    v.as.integer = 0;
    return v;
}

static inline Value val_bool(bool b) {
    Value v;
    v.type = VAL_BOOL;
    v.as.boolean = b;
    return v;
}

static inline Value val_int_val(long long n) {
    Value v;
    v.type = VAL_INT;
    v.as.integer = n;
    return v;
}

static inline Value val_number(double n) {
    Value v;
    v.type = VAL_NUMBER;
    v.as.number = n;
    return v;
}

static inline Value val_string(const char* s) {
    if (!s) s = "";
    int len = (int)strlen(s);
    ObjString* str = (ObjString*)malloc(sizeof(ObjString) + len + 1);
    str->length = len;
    memcpy(str->chars, s, len + 1);
    Value v;
    v.type = VAL_STRING;
    v.as.string = str;
    return v;
}

static inline bool is_numeric(Value v) {
    return v.type == VAL_INT || v.type == VAL_NUMBER;
}

static inline double as_double(Value v) {
    if (v.type == VAL_INT) return (double)v.as.integer;
    if (v.type == VAL_NUMBER) return v.as.number;
    return 0.0;
}

static inline bool val_is_truthy(Value v) {
    switch (v.type) {
        case VAL_NIL: return false;
        case VAL_BOOL: return v.as.boolean;
        case VAL_INT: return v.as.integer != 0;
        case VAL_NUMBER: return v.as.number != 0.0;
        case VAL_STRING: return v.as.string->length > 0;
        default: return true;
    }
}

// Convert any value to string
static inline char* val_to_cstr(Value v) {
    char buffer[256];
    switch (v.type) {
        case VAL_NIL:
            return strdup("nil");
        case VAL_BOOL:
            return strdup(v.as.boolean ? "true" : "false");
        case VAL_INT:
            snprintf(buffer, sizeof(buffer), "%lld", v.as.integer);
            return strdup(buffer);
        case VAL_NUMBER: {
            double n = v.as.number;
            if (n == (long long)n) {
                snprintf(buffer, sizeof(buffer), "%.1f", n);
            } else {
                snprintf(buffer, sizeof(buffer), "%g", n);
            }
            return strdup(buffer);
        }
        case VAL_STRING:
            return strdup(v.as.string->chars);
        case VAL_CLASS:
            snprintf(buffer, sizeof(buffer), "<class %s>", v.as.klass->name);
            return strdup(buffer);
        case VAL_INSTANCE:
            snprintf(buffer, sizeof(buffer), "<instance %s>", v.as.instance->klass->name);
            return strdup(buffer);
        case VAL_METHOD:
            return strdup("<bound method>");
        default:
            return strdup("<object>");
    }
}

// Printing
static inline void val_print_raw(Value v) {
    switch (v.type) {
        case VAL_NIL:
            printf("nil");
            break;
        case VAL_BOOL:
            printf(v.as.boolean ? "true" : "false");
            break;
        case VAL_INT:
            printf("%lld", v.as.integer);
            break;
        case VAL_NUMBER: {
            double n = v.as.number;
            if (n == (long long)n) {
                printf("%.1f", n);
            } else {
                printf("%g", n);
            }
            break;
        }
        case VAL_STRING:
            printf("%s", v.as.string->chars);
            break;
        case VAL_LIST: {
            printf("[");
            for (int i = 0; i < v.as.list->count; i++) {
                if (i > 0) printf(", ");
                val_print_raw(v.as.list->items[i]);
            }
            printf("]");
            break;
        }
        case VAL_DICT: {
            printf("{");
            for (int i = 0; i < v.as.dict->count; i++) {
                if (i > 0) printf(", ");
                printf("\"%s\": ", v.as.dict->entries[i].key);
                val_print_raw(v.as.dict->entries[i].value);
            }
            printf("}");
            break;
        }
        case VAL_CLASS:
            printf("<class %s>", v.as.klass->name);
            break;
        case VAL_INSTANCE:
            printf("<instance %s>", v.as.instance->klass->name);
            break;
        case VAL_METHOD:
            printf("<bound method>");
            break;
    }
}

static inline Value val_print(Value v) {
    val_print_raw(v);
    printf("\n");
    return val_nil();
}

// Operators
static inline Value val_add(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_int_val(a.as.integer + b.as.integer);
    }
    if (is_numeric(a) && is_numeric(b)) {
        return val_number(as_double(a) + as_double(b));
    }
    if (a.type == VAL_STRING || b.type == VAL_STRING) {
        char* sa = val_to_cstr(a);
        char* sb = val_to_cstr(b);
        int len = (int)(strlen(sa) + strlen(sb));
        char* res = (char*)malloc(len + 1);
        strcpy(res, sa);
        strcat(res, sb);
        Value result = val_string(res);
        free(sa);
        free(sb);
        free(res);
        return result;
    }
    return val_int_val(0);
}

static inline Value val_sub(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_int_val(a.as.integer - b.as.integer);
    }
    return val_number(as_double(a) - as_double(b));
}

static inline Value val_mul(Value a, Value b) {
    if (a.type == VAL_STRING && is_numeric(b)) {
        int times = (int)as_double(b);
        if (times <= 0) return val_string("");
        int slen = a.as.string->length;
        char* res = (char*)malloc(slen * times + 1);
        res[0] = '\0';
        for (int i = 0; i < times; i++) {
            strcat(res, a.as.string->chars);
        }
        Value v = val_string(res);
        free(res);
        return v;
    }
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_int_val(a.as.integer * b.as.integer);
    }
    return val_number(as_double(a) * as_double(b));
}

static inline Value val_div(Value a, Value b) {
    double db = as_double(b);
    if (db == 0.0) db = 1.0;
    return val_number(as_double(a) / db);
}

static inline Value val_mod(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        long long ib = b.as.integer != 0 ? b.as.integer : 1;
        return val_int_val(a.as.integer % ib);
    }
    double db = as_double(b);
    if (db == 0.0) db = 1.0;
    return val_number(fmod(as_double(a), db));
}

static inline Value val_negate(Value a) {
    if (a.type == VAL_INT) return val_int_val(-a.as.integer);
    return val_number(-as_double(a));
}

static inline Value val_not(Value a) {
    return val_bool(!val_is_truthy(a));
}

static inline Value val_equal(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_bool(a.as.integer == b.as.integer);
    }
    if (is_numeric(a) && is_numeric(b)) {
        return val_bool(as_double(a) == as_double(b));
    }
    if (a.type != b.type) {
        return val_bool(false);
    }
    switch (a.type) {
        case VAL_NIL: return val_bool(true);
        case VAL_BOOL: return val_bool(a.as.boolean == b.as.boolean);
        case VAL_STRING: return val_bool(strcmp(a.as.string->chars, b.as.string->chars) == 0);
        default: return val_bool(false);
    }
}

static inline Value val_not_equal(Value a, Value b) {
    Value eq = val_equal(a, b);
    return val_bool(!eq.as.boolean);
}

static inline Value val_less(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_bool(a.as.integer < b.as.integer);
    }
    if (is_numeric(a) && is_numeric(b)) {
        return val_bool(as_double(a) < as_double(b));
    }
    if (a.type == VAL_STRING && b.type == VAL_STRING) {
        return val_bool(strcmp(a.as.string->chars, b.as.string->chars) < 0);
    }
    return val_bool(false);
}

static inline Value val_less_equal(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_bool(a.as.integer <= b.as.integer);
    }
    if (is_numeric(a) && is_numeric(b)) {
        return val_bool(as_double(a) <= as_double(b));
    }
    if (a.type == VAL_STRING && b.type == VAL_STRING) {
        return val_bool(strcmp(a.as.string->chars, b.as.string->chars) <= 0);
    }
    return val_bool(false);
}

static inline Value val_greater(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_bool(a.as.integer > b.as.integer);
    }
    if (is_numeric(a) && is_numeric(b)) {
        return val_bool(as_double(a) > as_double(b));
    }
    if (a.type == VAL_STRING && b.type == VAL_STRING) {
        return val_bool(strcmp(a.as.string->chars, b.as.string->chars) > 0);
    }
    return val_bool(false);
}

static inline Value val_greater_equal(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_bool(a.as.integer >= b.as.integer);
    }
    if (is_numeric(a) && is_numeric(b)) {
        return val_bool(as_double(a) >= as_double(b));
    }
    if (a.type == VAL_STRING && b.type == VAL_STRING) {
        return val_bool(strcmp(a.as.string->chars, b.as.string->chars) >= 0);
    }
    return val_bool(false);
}

// Lists
static inline Value val_make_list(int count, Value* items) {
    ObjList* list = (ObjList*)malloc(sizeof(ObjList));
    list->count = count;
    list->capacity = count < 8 ? 8 : count * 2;
    list->items = (Value*)malloc(sizeof(Value) * list->capacity);
    for (int i = 0; i < count; i++) {
        list->items[i] = items[i];
    }
    Value v;
    v.type = VAL_LIST;
    v.as.list = list;
    return v;
}

static inline Value val_append(Value list, Value elem) {
    if (list.type != VAL_LIST) return val_nil();
    ObjList* l = list.as.list;
    if (l->count >= l->capacity) {
        l->capacity = l->capacity * 2;
        l->items = (Value*)realloc(l->items, sizeof(Value) * l->capacity);
    }
    l->items[l->count++] = elem;
    return val_nil();
}

static inline Value val_pop(Value list) {
    if (list.type != VAL_LIST) return val_nil();
    ObjList* l = list.as.list;
    if (l->count == 0) return val_nil();
    return l->items[--l->count];
}

// Dictionaries
static inline Value val_make_dict(int count, const char** keys, Value* values) {
    ObjDict* dict = (ObjDict*)malloc(sizeof(ObjDict));
    dict->count = count;
    dict->capacity = count < 8 ? 8 : count * 2;
    dict->entries = (DictEntry*)malloc(sizeof(DictEntry) * dict->capacity);
    for (int i = 0; i < count; i++) {
        dict->entries[i].key = strdup(keys[i]);
        dict->entries[i].value = values[i];
    }
    Value v;
    v.type = VAL_DICT;
    v.as.dict = dict;
    return v;
}

static inline Value val_get_index(Value target, Value index) {
    if (target.type == VAL_LIST) {
        int idx = (int)as_double(index);
        ObjList* l = target.as.list;
        if (idx < 0) idx = l->count + idx;
        if (idx >= 0 && idx < l->count) {
            return l->items[idx];
        }
        return val_nil();
    }
    if (target.type == VAL_DICT && index.type == VAL_STRING) {
        ObjDict* d = target.as.dict;
        for (int i = 0; i < d->count; i++) {
            if (strcmp(d->entries[i].key, index.as.string->chars) == 0) {
                return d->entries[i].value;
            }
        }
        return val_nil();
    }
    if (target.type == VAL_STRING && is_numeric(index)) {
        int idx = (int)as_double(index);
        ObjString* s = target.as.string;
        if (idx < 0) idx = s->length + idx;
        if (idx >= 0 && idx < s->length) {
            char buf[2] = { s->chars[idx], '\0' };
            return val_string(buf);
        }
        return val_nil();
    }
    return val_nil();
}

static inline Value val_set_index(Value target, Value index, Value val) {
    if (target.type == VAL_LIST) {
        int idx = (int)as_double(index);
        ObjList* l = target.as.list;
        if (idx < 0) idx = l->count + idx;
        if (idx >= 0 && idx < l->count) {
            l->items[idx] = val;
        }
        return val;
    }
    if (target.type == VAL_DICT && index.type == VAL_STRING) {
        ObjDict* d = target.as.dict;
        for (int i = 0; i < d->count; i++) {
            if (strcmp(d->entries[i].key, index.as.string->chars) == 0) {
                d->entries[i].value = val;
                return val;
            }
        }
        if (d->count >= d->capacity) {
            d->capacity = d->capacity * 2;
            d->entries = (DictEntry*)realloc(d->entries, sizeof(DictEntry) * d->capacity);
        }
        d->entries[d->count].key = strdup(index.as.string->chars);
        d->entries[d->count].value = val;
        d->count++;
        return val;
    }
    return val;
}

// Builtins
static inline Value val_len(Value v) {
    if (v.type == VAL_LIST) return val_int_val(v.as.list->count);
    if (v.type == VAL_STRING) return val_int_val(v.as.string->length);
    if (v.type == VAL_DICT) return val_int_val(v.as.dict->count);
    return val_int_val(0);
}

static inline Value val_keys(Value dict) {
    if (dict.type != VAL_DICT) return val_make_list(0, NULL);
    ObjDict* d = dict.as.dict;
    Value* items = (Value*)malloc(sizeof(Value) * d->count);
    for (int i = 0; i < d->count; i++) {
        items[i] = val_string(d->entries[i].key);
    }
    Value res = val_make_list(d->count, items);
    free(items);
    return res;
}

static inline Value val_values(Value dict) {
    if (dict.type != VAL_DICT) return val_make_list(0, NULL);
    ObjDict* d = dict.as.dict;
    Value* items = (Value*)malloc(sizeof(Value) * d->count);
    for (int i = 0; i < d->count; i++) {
        items[i] = d->entries[i].value;
    }
    Value res = val_make_list(d->count, items);
    free(items);
    return res;
}

static inline Value val_str(Value v) {
    char* s = val_to_cstr(v);
    Value res = val_string(s);
    free(s);
    return res;
}

static inline Value val_int(Value v) {
    if (v.type == VAL_INT) return v;
    if (v.type == VAL_NUMBER) return val_int_val((long long)v.as.number);
    if (v.type == VAL_STRING) return val_int_val(atoll(v.as.string->chars));
    if (v.type == VAL_BOOL) return val_int_val(v.as.boolean ? 1 : 0);
    return val_int_val(0);
}

static inline Value val_float(Value v) {
    if (v.type == VAL_NUMBER) return v;
    if (v.type == VAL_INT) return val_number((double)v.as.integer);
    if (v.type == VAL_STRING) return val_number(atof(v.as.string->chars));
    if (v.type == VAL_BOOL) return val_number(v.as.boolean ? 1.0 : 0.0);
    return val_number(0.0);
}

static inline Value val_type_name(Value v) {
    switch (v.type) {
        case VAL_NIL: return val_string("nil");
        case VAL_BOOL: return val_string("bool");
        case VAL_INT:
        case VAL_NUMBER: return val_string("number");
        case VAL_STRING: return val_string("string");
        case VAL_LIST: return val_string("list");
        case VAL_DICT: return val_string("dict");
        case VAL_CLASS: return val_string("class");
        case VAL_INSTANCE: return val_string("instance");
        case VAL_METHOD: return val_string("method");
        default: return val_string("object");
    }
}

static inline Value val_clock(void) {
    return val_number((double)clock() / CLOCKS_PER_SEC);
}

// Math functions
static inline Value val_abs(Value v) {
    if (v.type == VAL_INT) return val_int_val(llabs(v.as.integer));
    return val_number(fabs(as_double(v)));
}

static inline Value val_sqrt(Value v) {
    return val_number(sqrt(as_double(v)));
}

static inline Value val_min(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_int_val(a.as.integer < b.as.integer ? a.as.integer : b.as.integer);
    }
    return val_number(as_double(a) < as_double(b) ? as_double(a) : as_double(b));
}

static inline Value val_max(Value a, Value b) {
    if (a.type == VAL_INT && b.type == VAL_INT) {
        return val_int_val(a.as.integer > b.as.integer ? a.as.integer : b.as.integer);
    }
    return val_number(as_double(a) > as_double(b) ? as_double(a) : as_double(b));
}

// File I/O
static inline Value val_read_file(Value path) {
    if (path.type != VAL_STRING) return val_nil();
    FILE* f = fopen(path.as.string->chars, "rb");
    if (!f) return val_nil();
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc(size + 1);
    fread(buf, 1, size, f);
    buf[size] = '\0';
    fclose(f);
    Value res = val_string(buf);
    free(buf);
    return res;
}

static inline Value val_write_file(Value path, Value content) {
    if (path.type != VAL_STRING) return val_bool(false);
    FILE* f = fopen(path.as.string->chars, "wb");
    if (!f) return val_bool(false);
    char* text = val_to_cstr(content);
    fputs(text, f);
    free(text);
    fclose(f);
    return val_bool(true);
}

static inline Value val_remove_file(Value path) {
    if (path.type != VAL_STRING) return val_bool(false);
    return val_bool(remove(path.as.string->chars) == 0);
}

// Classes and Objects
static inline Value val_make_class(const char* name, ObjClass* superclass) {
    ObjClass* k = (ObjClass*)malloc(sizeof(ObjClass));
    k->name = strdup(name);
    k->superclass = superclass;
    k->method_count = 0;
    Value v;
    v.type = VAL_CLASS;
    v.as.klass = k;
    return v;
}

static inline void val_class_add_method(ObjClass* k, const char* name, MethodFn fn) {
    if (k->method_count < 64) {
        k->methods[k->method_count].name = strdup(name);
        k->methods[k->method_count].fn = fn;
        k->method_count++;
    }
}

static inline MethodFn val_class_find_method(ObjClass* k, const char* name) {
    ObjClass* curr = k;
    while (curr) {
        for (int i = 0; i < curr->method_count; i++) {
            if (strcmp(curr->methods[i].name, name) == 0) {
                return curr->methods[i].fn;
            }
        }
        curr = curr->superclass;
    }
    return NULL;
}

static inline Value val_instantiate(ObjClass* k, int arg_count, Value* args) {
    ObjInstance* inst = (ObjInstance*)malloc(sizeof(ObjInstance));
    inst->klass = k;
    inst->field_count = 0;
    Value v;
    v.type = VAL_INSTANCE;
    v.as.instance = inst;

    MethodFn init_fn = val_class_find_method(k, "init");
    if (init_fn) {
        init_fn(v, arg_count, args);
    }
    return v;
}

static inline Value val_get_property(Value target, const char* prop) {
    if (target.type != VAL_INSTANCE) return val_nil();
    ObjInstance* inst = target.as.instance;
    for (int i = 0; i < inst->field_count; i++) {
        if (strcmp(inst->fields[i].name, prop) == 0) {
            return inst->fields[i].value;
        }
    }
    MethodFn fn = val_class_find_method(inst->klass, prop);
    if (fn) {
        ObjMethod* m = (ObjMethod*)malloc(sizeof(ObjMethod));
        m->receiver = target;
        m->fn = fn;
        Value res;
        res.type = VAL_METHOD;
        res.as.method = m;
        return res;
    }
    return val_nil();
}

static inline Value val_set_property(Value target, const char* prop, Value val) {
    if (target.type != VAL_INSTANCE) return val;
    ObjInstance* inst = target.as.instance;
    for (int i = 0; i < inst->field_count; i++) {
        if (strcmp(inst->fields[i].name, prop) == 0) {
            inst->fields[i].value = val;
            return val;
        }
    }
    if (inst->field_count < 64) {
        inst->fields[inst->field_count].name = strdup(prop);
        inst->fields[inst->field_count].value = val;
        inst->field_count++;
    }
    return val;
}

static inline Value val_call_method(Value target, const char* prop, int arg_count, Value* args) {
    if (target.type == VAL_METHOD) {
        return target.as.method->fn(target.as.method->receiver, arg_count, args);
    }
    if (target.type == VAL_INSTANCE) {
        MethodFn fn = val_class_find_method(target.as.instance->klass, prop);
        if (fn) {
            return fn(target, arg_count, args);
        }
    }
    return val_nil();
}

#endif // SIMPLE_RUNTIME_H
