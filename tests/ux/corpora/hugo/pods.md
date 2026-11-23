---
title: Ephemeral containers
---

{{< feature-state state="stable" for_k8s_version="v1.25" >}}

This page explains ephemeral containers. You use them to debug a running Pod.

{{< note >}}
Ephemeral containers have no ports.
{{< /note >}}

{{% alert title="Warning" color="warning" %}}
Do not run them in production for long.
{{% /alert %}}

{% include "partials/footer.html" %}

The site version is {{ site.version }} today.
