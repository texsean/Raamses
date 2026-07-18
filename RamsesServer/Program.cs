using System;
using System.Collections.Generic;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Xml;

namespace RamsesServer
{
    class Program
    {
        private static readonly Dictionary<string, RegisteredDevice> registeredDevices = new Dictionary<string, RegisteredDevice>();
        private static readonly int MAX_FREE_DEVICES = 1;
        private static HttpListener listener;

        static void Main(string[] args)
        {
            Console.WriteLine("=== Ramses Agent Monitor Server ===");
            Console.WriteLine("Free tier: 1 device. Paid tier coming soon.\n");

            listener = new HttpListener();
            listener.Prefixes.Add("http://+:8080/");
            listener.Start();

            Console.WriteLine("Server listening on http://localhost:8080");
            Console.WriteLine("Devices should connect to your IP:8080/register and /stats\n");

            ThreadPool.QueueUserWorkItem((_) => HandleRequests());

            Console.WriteLine("Press Enter to stop server...");
            Console.ReadLine();
            listener.Stop();
        }

        private static void HandleRequests()
        {
            while (listener.IsListening)
            {
                var context = listener.GetContext();
                ThreadPool.QueueUserWorkItem((_) => ProcessRequest(context));
            }
        }

        private static void ProcessRequest(HttpListenerContext context)
        {
            var request = context.Request;
            var response = context.Response;
            string path = request.Url.AbsolutePath.ToLower();

            Console.WriteLine($"Request: {path}");

            if (path == "/register")
            {
                HandleRegistration(request, response);
            }
            else if (path == "/stats")
            {
                ServeStats(response);
            }
            else
            {
                response.StatusCode = 404;
                byte[] buffer = Encoding.UTF8.GetBytes("<h1>404 - Ramses Server</h1>");
                response.ContentLength64 = buffer.Length;
                response.OutputStream.Write(buffer, 0, buffer.Length);
            }

            response.Close();
        }

        private static void HandleRegistration(HttpListenerRequest request, HttpListenerResponse response)
        {
            string macMd5 = request.QueryString["mac"] ?? "unknown";
            
            if (!registeredDevices.ContainsKey(macMd5))
            {
                if (registeredDevices.Count < MAX_FREE_DEVICES)
                {
                    registeredDevices[macMd5] = new RegisteredDevice
                    {
                        MacMd5 = macMd5,
                        RegisteredAt = DateTime.Now,
                        Ip = request.RemoteEndPoint.ToString()
                    };
                    Console.WriteLine($"Device registered: {macMd5}");
                    SendXmlResponse(response, "<status>registered</status><message>Welcome to free tier</message>");
                }
                else
                {
                    SendXmlResponse(response, "<status>full</status><message>Free tier full. Upgrade for more devices.</message>");
                }
            }
            else
            {
                SendXmlResponse(response, "<status>already_registered</status><message>Device already registered.</message>");
            }
        }

        private static void ServeStats(HttpListenerResponse response)
        {
            var xml = new XmlDocument();
            var root = xml.CreateElement("ramses");
            xml.AppendChild(root);

            AddElement(xml, root, "agents", "4");
            AddElement(xml, root, "subagents", "7");
            AddElement(xml, root, "project", "PCI-SSS-2.0");
            AddElement(xml, root, "progress", "67");
            AddElement(xml, root, "tokens_total", "18420");
            AddElement(xml, root, "tokens_last_hour", "3240");
            AddElement(xml, root, "sprint", "4 of 7");
            AddElement(xml, root, "status", "green");
            AddElement(xml, root, "last_alert", "Server 2 requesting permission");

            using (var sw = new System.IO.StringWriter())
            {
                xml.Save(sw);
                string xmlString = sw.ToString();
                byte[] buffer = Encoding.UTF8.GetBytes(xmlString);
                response.ContentType = "application/xml";
                response.ContentLength64 = buffer.Length;
                response.OutputStream.Write(buffer, 0, buffer.Length);
            }
        }

        private static void AddElement(XmlDocument doc, XmlElement parent, string name, string value)
        {
            var el = doc.CreateElement(name);
            el.InnerText = value;
            parent.AppendChild(el);
        }

        private static void SendXmlResponse(HttpListenerResponse response, string xmlContent)
        {
            string fullXml = $"<ramses>{xmlContent}</ramses>";
            byte[] buffer = Encoding.UTF8.GetBytes(fullXml);
            response.ContentType = "application/xml";
            response.ContentLength64 = buffer.Length;
            response.OutputStream.Write(buffer, 0, buffer.Length);
        }
    }

    class RegisteredDevice
    {
        public string MacMd5 { get; set; }
        public DateTime RegisteredAt { get; set; }
        public string Ip { get; set; }
    }
}
