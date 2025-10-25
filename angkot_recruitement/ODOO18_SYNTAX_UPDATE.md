# Odoo 18 Syntax Update - View Attributes

## Overview
Since Odoo 17.0, major view syntax changes have been introduced:
1. The `attrs` and `states` attributes are deprecated
2. The `<tree>` tag has been renamed to `<list>`

This document outlines all changes made to comply with Odoo 18 standards.

## Key Changes

### 1. Deprecated `attrs` Attribute
The `attrs` attribute using domain-like expressions is no longer supported.

**Old Syntax (Odoo 16 and earlier):**
```xml
<field name="end_date" attrs="{'invisible': [('is_current', '=', True)]}"/>
<field name="credential_url" attrs="{'readonly': [('is_verified', '=', True)]}"/>
<field name="button" attrs="{'invisible': [('field_id', '=', False)]}"/>
```

**New Syntax (Odoo 18):**
```xml
<field name="end_date" invisible="is_current"/>
<field name="credential_url" readonly="is_verified"/>
<field name="button" invisible="not field_id"/>
```

### 2. Tree Views Renamed to List Views

The `<tree>` tag has been completely replaced with `<list>` in Odoo 18.

**Old Syntax (Odoo 16 and earlier):**
```xml
<tree string="Education">
    <field name="school"/>
    <field name="degree"/>
</tree>
```

**New Syntax (Odoo 18):**
```xml
<list string="Education">
    <field name="school"/>
    <field name="degree"/>
</list>
```

**Important Notes:**
- View mode is still called `tree` in action definitions
- Only the XML tag name changes from `<tree>` to `<list>`
- All tree view attributes work the same way with `<list>`
- Applies to both standalone views and inline One2many/Many2many views

### 3. Direct Python Expressions
The new syntax uses direct Python expressions instead of domain notation.

**Comparison:**
| Old Domain Syntax | New Python Expression |
|------------------|----------------------|
| `[('field', '=', True)]` | `field` |
| `[('field', '=', False)]` | `not field` |
| `[('field', '!=', False)]` | `field` |
| `[('field', '>', 0)]` | `field > 0` |
| `[('field', 'in', [1,2,3])]` | `field in [1,2,3]` |
| `['|', ('a','=',True), ('b','=',True)]` | `a or b` |
| `[('a','=',True), ('b','=',True)]` | `a and b` |

### 3. Multiple Attributes
You can now use multiple modifiers directly on the same element.

**Example:**
```xml
<field name="expiry_date" 
       invisible="not has_expiry"
       readonly="is_verified"
       required="certification_type == 'professional'"/>
```

## Changes Made in Our Views

### 1. Tree to List Conversion

All `<tree>` tags have been replaced with `<list>`:

**Files Updated:**
- `hr_candidate_profile_views.xml`: 5 views converted
- `hr_candidate_views.xml`: 4 inline views converted

**Examples:**
```xml
<!-- Before -->
<tree string="Education">
    <field name="school"/>
</tree>

<!-- After -->
<list string="Education">
    <field name="school"/>
</list>
```

### 2. Education Form View (`hr_candidate_profile_views.xml`)
```xml
<!-- Before -->
<field name="end_date" attrs="{'invisible': [('is_current', '=', True)]}"/>

<!-- After -->
<field name="end_date" invisible="is_current"/>
```

### 2. Experience Form View (`hr_candidate_profile_views.xml`)
```xml
<!-- Before -->
<field name="end_date" attrs="{'invisible': [('is_current', '=', True)]}"/>

<!-- After -->
<field name="end_date" invisible="is_current"/>
```

### 3. Certification Form View (`hr_candidate_profile_views.xml`)
```xml
<!-- Before -->
<button name="action_open_credential_url" 
        attrs="{'invisible': [('credential_url', '=', False)]}"/>

<!-- After -->
<button name="action_open_credential_url" 
        invisible="not credential_url"/>
```

### 4. Candidate Views (`hr_candidate_views.xml`)
All inline form views within One2many fields use the correct syntax:
```xml
<field name="end_date" invisible="is_current"/>
<button invisible="not credential_url">
<field name="is_expired" column_invisible="1"/>
<page invisible="not extraction_log">
```

## Tree View Updates

### Column Visibility
For tree/list views, use `column_invisible` instead of `invisible`:

```xml
<!-- For hiding columns in tree view -->
<field name="is_expired" column_invisible="1"/>
<field name="is_expiring_soon" column_invisible="1"/>
```

### Tree Decorations
Tree decorations remain the same but reference fields directly:

```xml
<tree decoration-danger="is_expired" 
      decoration-warning="is_expiring_soon">
    <field name="name"/>
    <field name="status_display"/>
    <field name="is_expired" column_invisible="1"/>
    <field name="is_expiring_soon" column_invisible="1"/>
</tree>
```

## Benefits of New Syntax

1. **Simpler**: Direct Python expressions are easier to read and write
2. **More Powerful**: Full Python expression support
3. **Better Performance**: No need to parse domain notation
4. **IDE Support**: Better syntax highlighting and validation
5. **Consistency**: Aligns with Python code style

## Common Patterns

### Boolean Fields
```xml
<!-- Show when True -->
<field name="field_name" invisible="not boolean_field"/>

<!-- Show when False -->
<field name="field_name" invisible="boolean_field"/>
```

### Comparison
```xml
<!-- Equal to -->
<field name="field_name" invisible="other_field == 'value'"/>

<!-- Not equal to -->
<field name="field_name" invisible="other_field != 'value'"/>

<!-- Greater than -->
<field name="field_name" invisible="count &lt; 5"/>

<!-- Less than -->
<field name="field_name" invisible="count &gt; 10"/>
```

### Multiple Conditions
```xml
<!-- AND condition -->
<field name="field_name" invisible="field_a and field_b"/>

<!-- OR condition -->
<field name="field_name" invisible="field_a or field_b"/>

<!-- Complex condition -->
<field name="field_name" 
       invisible="(status == 'draft' and not approved) or archived"/>
```

### Selection Fields
```xml
<field name="field_name" invisible="state in ['draft', 'cancel']"/>
<field name="field_name" invisible="state not in ['done', 'posted']"/>
```

## Migration Checklist

When migrating from older Odoo versions:

- [ ] Replace all `attrs` with direct attributes
- [ ] Convert domain expressions to Python expressions
- [ ] Update boolean checks (`[('field', '=', True)]` → `field`)
- [ ] Update negation (`[('field', '=', False)]` → `not field`)
- [ ] Use `column_invisible` in tree views
- [ ] Test all conditional visibility/readonly/required logic
- [ ] Update documentation

## Best Practices

1. **Keep It Simple**: Use direct field references when possible
   ```xml
   <!-- Good -->
   <field invisible="not active"/>
   
   <!-- Avoid -->
   <field invisible="active == False"/>
   ```

2. **Use Parentheses**: For complex conditions, use parentheses for clarity
   ```xml
   <field invisible="(status == 'draft' and not approved) or (status == 'cancel')"/>
   ```

3. **Boolean Context**: Remember that many fields are truthy/falsy
   ```xml
   <!-- Many2one field - checks if set -->
   <field invisible="not partner_id"/>
   
   <!-- Integer field - checks if > 0 -->
   <field invisible="not count"/>
   
   <!-- Char field - checks if not empty -->
   <field invisible="not name"/>
   ```

4. **Computed Fields**: Can be used in expressions
   ```xml
   <field invisible="total_amount &lt; 1000"/>
   ```

## Testing

After migration, thoroughly test:

1. **Field Visibility**: Ensure fields show/hide correctly
2. **Readonly Logic**: Verify readonly conditions work
3. **Required Fields**: Test required field validation
4. **Button Visibility**: Check button visibility based on conditions
5. **Tree Decorations**: Verify row coloring and styling
6. **Notebook Pages**: Test tab visibility logic

## Resources

- [Odoo 17.0 Release Notes](https://www.odoo.com/odoo-17)
- [Odoo Documentation - Views](https://www.odoo.com/documentation/18.0/developer/reference/backend/views.html)
- [Odoo Upgrade Guide](https://www.odoo.com/documentation/18.0/developer/howtos/upgrade.html)

## Additional Important Changes

### Using `id` Instead of `active_id` in Form Views

When using context in inline One2many/Many2many fields within a form view, use `id` (the current record's ID field) instead of `active_id`:

**Correct:**
```xml
<field name="education_ids" context="{'default_candidate_id': id}">
```

**Incorrect:**
```xml
<field name="education_ids" context="{'default_candidate_id': active_id}">
```

**Why:** `active_id` is only available in the context when triggering actions, but `id` is always available as a field in form views. Using `active_id` will cause access rights inconsistency errors.

## Summary

All views in the `angkot_recruitement` module have been updated to use Odoo 18 syntax:

✅ **Education Views** - Updated
✅ **Experience Views** - Updated  
✅ **Certification Views** - Updated
✅ **Portfolio Views** - Updated
✅ **Candidate Views** - Updated
✅ **All `attrs` removed** - Replaced with direct attributes
✅ **All `<tree>` tags** - Replaced with `<list>`
✅ **Tree decorations** - Using correct syntax
✅ **Column visibility** - Using `column_invisible`
✅ **Context references** - Using `id` instead of `active_id`

The module is now fully compliant with Odoo 18 view standards and ready for production use.

