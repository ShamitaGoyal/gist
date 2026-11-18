# Page 4

## Figure Caption

Figure 3: The Meridian specification is made up of three main components: data binding, views, and malleability. First, data binding describes the mapping from a data source to attributes rendered in the ODI. Second, views describe what attributes are shown in which views, how views are composed, layouts of items, and how detail views are opened. Lastly, malleability specifies which customizations the end-user will have access to.

## Data Binding Specification

### Code

```text
1 {
dataBinding: [{
id: "query",
binding: {
itemId: ".itemId",
attributes: [
value: ".name", roles: ["title"] },
value: ".details.photo",
type: "image",
roles: ["thumbnail"]
},
value: ".details.rating", roles: ["subtitle"], },
roles: ["subtitle"],
attributes: [
value: ".address_obj.street1" },
value: ".address_obj.street2",
condition: { exists: ".address_obj.street2" }
{ value: ".address_obj.city" },
{ value: ".address_obj.country" },
},
value: ".details.price_level", roles: ["tag"] },
value: ".details.amenities",
roles: ["spec"],
transform: [{ map: ".amenity" }]
},
[uncertain: ],]
}
}],
```

### Explanations

1. Reference the data source for data binding
2. Reference values from data with the prefix "."
3. Assign attributes with type to describe how they are rendered and roles map to where they are shown in the view.
4. Attributes can contain multiple attributes.
5. Conditionals can determine whether an attribute should or should not be rendered.
6. Attributes carrying lists of attributes can transform into an attribute group by mapping or filtering.

## View Specification

### Code

```text
overviews: [
type: "list",
itemView: { type: "compact" },
shownAttributes: ["title", "subtitle", "thumbnail",
"key-attribute", "action", "link"]
},
{
type: "grid",
detailViews: [
type: "full",
openFrom: ["title"],
openIn: "side-by-side",
openBy: "click",
overviews: [
showIn: "footer",
bindingId: "recommended",
type: "carousel"
detailViews: [
type: "gallery",
openFrom: ["thumbnail"],
shownAttributes: ["thumbnail"]
[uncertain: {]
{
],
},
],
detailViews: [
{ id: "article", type: "article" }
```

### Explanations

7. Define the overview type. Other properties can additionally be defined such as the item view type and which attributes to show.
8. Detail views are defined inside overviews, and can be defined with a type, which specifies the elements that open the view, where to open it in, and how to select it.
9. Compose views in detail views.
10. Specify where to display composed overviews. Overviews can also reference different data sources with bindingId, such as a list of recommended items.
11. Detail views can also specify which attributes to show or hide.
12. Define detail views independently from overviews. Overviews can reference external detail views via id.

### Diagram labels

- list with compact items
- click "title"
- open side-by-side
- carousel
- gallery detail view

## Malleability Specification

### Code

```text
malleability: {
content:
types: ["toggle"]
},
composition: {
disabled: true
layout: {
types: ["menus"]
}
}
{ε8
```

### Explanations

13. Specify malleability features for each dimension, and how the features are shown in the UI.
14. All malleability features are enabled by default, but can be disabled through the specification.

### Diagram labels

- toggle to customize
- shown attributes
